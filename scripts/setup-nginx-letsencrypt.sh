#!/usr/bin/env bash
set -euo pipefail

# Quick setup for Nginx + Let's Encrypt on a Ubuntu/Debian droplet.
# Proxies HTTPS traffic to a local backend (default 127.0.0.1:8000).
#
# Required env:
#   DOMAIN          e.g. api.example.com
# Optional env:
#   EMAIL           Email for Let's Encrypt notifications (default: admin@${DOMAIN})
#   BACKEND_PORT    Local backend port (default: 8000)

: "${DOMAIN:?Set DOMAIN (e.g., api.example.com)}"
EMAIL=${EMAIL:-"admin@${DOMAIN}"}
BACKEND_PORT=${BACKEND_PORT:-8000}

echo "Installing Nginx and Certbot..."
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

CONF_PATH="/etc/nginx/sites-available/cybergrader"
sudo tee "$CONF_PATH" >/dev/null <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ { root /var/www/html; }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN};

    # SSL will be configured by certbot; placeholders here.
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Proxy to backend
    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

sudo ln -sf "$CONF_PATH" /etc/nginx/sites-enabled/cybergrader
sudo nginx -t
sudo systemctl restart nginx

echo "Requesting Let's Encrypt certificate for ${DOMAIN}"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

echo "Auto-renewal status:"
sudo systemctl status certbot.timer --no-pager || true
echo "You can test renewal with: sudo certbot renew --dry-run"

