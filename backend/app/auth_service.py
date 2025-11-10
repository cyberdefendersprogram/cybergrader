from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
import psycopg
from passlib.context import CryptContext
from psycopg import sql


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, dsn: Optional[str], schema: str = "public") -> None:
        self.dsn = dsn
        self.schema = schema
        self.secret = os.getenv("SECRET_KEY", "insecure-dev-key")
        self.jwt_algo = "HS256"
        # Password hashing context: bcrypt_sha256
        self.pwd_ctx = CryptContext(schemes=["bcrypt_sha256"])

        # Email settings (ForwardEmail API)
        self.fe_api_token = os.getenv("FORWARDEMAIL_API_TOKEN")
        self.email_from = os.getenv("EMAIL_FROM")
        self.reset_link_base = os.getenv("RESET_LINK_BASE")

    # ------------------------------------------------------------------
    # Utility
    def _qualified(self, table: str) -> sql.Composed:
        return sql.SQL("{}.{}" ).format(sql.Identifier(self.schema), sql.Identifier(table))

    # ------------------------------------------------------------------
    # Core operations
    def signup(self, email: str, password: str) -> dict:
        self._require_db()
        email_lc = email.strip().lower()
        user_id = str(uuid.uuid4())
        pw_hash = self.pwd_ctx.hash(password, scheme="bcrypt_sha256")

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {} (id, email, password_hash, role)
                        VALUES (%s, %s, %s, 'student')
                        ON CONFLICT (email) DO NOTHING
                        RETURNING id, email, role, student_id
                        """
                    ).format(self._qualified("users")),
                    (user_id, email_lc, pw_hash),
                )
                row = cur.fetchone()
                if row is None:
                    # User exists already: fetch it and verify password
                    cur.execute(
                        sql.SQL("SELECT id, email, role, student_id, password_hash FROM {} WHERE email=%s" ).format(
                            self._qualified("users")
                        ),
                        (email_lc,),
                    )
                    existing = cur.fetchone()
                    if existing is None:
                        raise AuthError("Unable to create or fetch user")
                    # Allow idempotent signup = login if password matches
                    if not self.pwd_ctx.verify(password, existing[4]):
                        raise AuthError("User already exists")
                    user = {"id": existing[0], "email": existing[1], "role": existing[2], "student_id": existing[3]}
                else:
                    user = {"id": row[0], "email": row[1], "role": row[2], "student_id": row[3]}
            conn.commit()
        return user

    def login(self, email: str, password: str) -> dict:
        self._require_db()
        email_lc = email.strip().lower()
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT id, email, role, student_id, password_hash FROM {} WHERE email=%s" ).format(
                        self._qualified("users")
                    ),
                    (email_lc,),
                )
                row = cur.fetchone()
                if row is None or not self.pwd_ctx.verify(password, row[4]):
                    raise AuthError("Invalid credentials")
                user = {"id": row[0], "email": row[1], "role": row[2], "student_id": row[3]}
        return user

    def set_student_id(self, user_id: str, student_id: str) -> None:
        self._require_db()
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        sql.SQL("UPDATE {} SET student_id=%s, updated_at=NOW() WHERE id=%s" ).format(
                            self._qualified("users")
                        ),
                        (student_id.strip(), user_id),
                    )
                except Exception as e:  # unique violation or other DB error
                    # psycopg 3 specific error code for unique_violation: 23505
                    code = getattr(e, "sqlstate", None)
                    if code == "23505":
                        raise AuthError("Student ID is already in use")
                    raise
            conn.commit()

    # ------------------------------------------------------------------
    # JWT helpers
    def issue_jwt(self, user: dict, expires_in_hours: int = 24) -> str:
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": int(time.time()) + expires_in_hours * 3600,
        }
        return jwt.encode(payload, self.secret, algorithm=self.jwt_algo)

    # ------------------------------------------------------------------
    # Password reset
    def request_password_reset(self, email: str) -> None:
        self._require_db()
        email_lc = email.strip().lower()
        user: Optional[tuple] = None
        token: Optional[str] = None
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT id FROM {} WHERE email=%s" ).format(self._qualified("users")), (email_lc,))
                row = cur.fetchone()
                if row:
                    user = row
                    # Cooldown: ensure no more than one token per minute
                    cur.execute(
                        sql.SQL(
                            "SELECT created_at FROM {} WHERE user_id=%s ORDER BY created_at DESC LIMIT 1"
                        ).format(self._qualified("password_reset_tokens")),
                        (row[0],),
                    )
                    last = cur.fetchone()
                    if last and (datetime.now(timezone.utc) - last[0]).total_seconds() < 60:
                        # Silently ignore to avoid enumeration/collisions
                        return
                    token = self._new_token()
                    expires = datetime.now(timezone.utc) + timedelta(hours=1)
                    cur.execute(
                        sql.SQL(
                            "INSERT INTO {} (user_id, token, expires_at) VALUES (%s, %s, %s)"
                        ).format(self._qualified("password_reset_tokens")),
                        (row[0], token, expires),
                    )
            conn.commit()
        if user and token:
            self._send_reset_email(email_lc, token)

    def reset_password(self, token: str, new_password: str) -> None:
        self._require_db()
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        "SELECT t.user_id, t.expires_at, t.used_at FROM {} t WHERE t.token=%s"
                    ).format(self._qualified("password_reset_tokens")),
                    (token,),
                )
                row = cur.fetchone()
                if row is None:
                    raise AuthError("Invalid token")
                user_id, expires_at, used_at = row
                if used_at is not None or expires_at < datetime.now(timezone.utc):
                    raise AuthError("Expired token")
                pw_hash = self.pwd_ctx.hash(new_password, scheme="bcrypt_sha256")
                cur.execute(
                    sql.SQL("UPDATE {} SET password_hash=%s, updated_at=NOW() WHERE id=%s" ).format(
                        self._qualified("users")
                    ),
                    (pw_hash, user_id),
                )
                cur.execute(
                    sql.SQL("UPDATE {} SET used_at=NOW() WHERE token=%s" ).format(
                        self._qualified("password_reset_tokens")
                    ),
                    (token,),
                )
            conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    def _new_token(self) -> str:
        return uuid.uuid4().hex + uuid.uuid4().hex

    def _send_reset_email(self, recipient: str, token: str) -> None:
        if not (self.fe_api_token and self.email_from and self.reset_link_base):
            return
        # The latest token for this user is used in the link
        link = f"{self.reset_link_base}?token={token}"
        subject = "Reset your Cyber Grader password"
        text = f"Click the link to reset your password: {link}\nThis link expires in 1 hour."
        html = f"<p>Click the link to reset your password:</p><p><a href=\"{link}\">Reset Password</a></p><p>This link expires in 1 hour.</p>"
        headers = {"Authorization": f"Bearer {self.fe_api_token}"}
        payload = {"from": self.email_from, "to": [recipient], "subject": subject, "text": text, "html": html}
        try:
            httpx.post("https://api.forwardemail.net/v1/emails", headers=headers, json=payload, timeout=10)
        except Exception:
            # Best-effort; do not raise
            pass

    def _require_db(self) -> None:
        if not self.dsn:
            raise AuthError("Database not configured") 
