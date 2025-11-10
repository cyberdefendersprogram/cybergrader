import { useEffect, useState } from "react";
import { api } from "../api";

interface NotesListProps {
  navigate: (path: string) => void;
}

export function NotesList({ navigate }: NotesListProps) {
  const [notes, setNotes] = useState<string[]>([]);

  useEffect(() => {
    api
      .listNotes()
      .then((r) => setNotes(r.notes || []))
      .catch(() => setNotes([]));
  }, []);

  return (
    <div className="card login-card" style={{ marginBottom: "1rem" }}>
      <h3 style={{ marginTop: 0 }}>Notes</h3>
      {notes.length === 0 ? (
        <p style={{ color: "var(--text-secondary)", margin: 0 }}>No notes available yet.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: ".5rem" }}>
          {notes.map((n) => (
            <li key={n}>
              <button type="button" className="secondary-button" onClick={() => navigate(`/notes/${encodeURIComponent(n)}`)}>
                {n}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

