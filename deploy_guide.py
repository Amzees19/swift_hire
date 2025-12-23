# Secure Deployment Guide
# Domain & DNS
# Acquire a domain (recommended) or use a trusted free DNS provider (e.g., DuckDNS/No-IP) and create an A/AAAA record pointing to your server’s public IP.
# Choose a single hostname (e.g., alerts.yourdomain.com) for the app.
# Server Setup
# Use a recent Linux distro on your VPS/VM/container.
# Install Python 3.11+, Git, and a C compiler for any wheels.
# Create a dedicated app user (e.g., appuser) with minimal privileges.
# Clone the repo to /opt/amazon_alerts (or your chosen path).
# Create and activate a virtualenv; install dependencies:
# python -m pip install -r requirements.txt
# python -m pip install httpx (for TestClient-based tests, if desired).
# Application Service
# Run Uvicorn bound to localhost only (don’t expose it directly):
# Example: python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --workers 4
# Manage it with systemd so it restarts on boot/crash. Example unit (/etc/systemd/system/amazon-alerts.service):
# [Unit]
# Description=Amazon Alerts API
# After=network.target

# [Service]
# User=appuser
# WorkingDirectory=/opt/amazon_alerts
# ExecStart=/opt/amazon_alerts/venv/bin/python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --workers 4
# Restart=always
# Environment="PYTHONUNBUFFERED=1"

# [Install]
# WantedBy=multi-user.target
# sudo systemctl daemon-reload && sudo systemctl enable --now amazon-alerts
# Reverse Proxy (HTTPS)
# Put Nginx or Caddy in front to terminate TLS and forward to 127.0.0.1:8000.
# Nginx example (/etc/nginx/sites-available/amazon_alerts):
# server {
#     listen 80;
#     server_name alerts.yourdomain.com;
#     return 301 https://$host$request_uri;
# }

# server {
#     listen 443 ssl http2;
#     server_name alerts.yourdomain.com;

#     ssl_certificate /etc/letsencrypt/live/alerts.yourdomain.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/alerts.yourdomain.com/privkey.pem;

#     add_header X-Content-Type-Options nosniff;
#     add_header X-Frame-Options SAMEORIGIN;
#     add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self' data:; connect-src 'self';";

#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }
# Enable and reload: ln -s /etc/nginx/sites-available/amazon_alerts /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx
# Get certs: certbot --nginx -d alerts.yourdomain.com
# Caddy alternative (/etc/caddy/Caddyfile):
# alerts.yourdomain.com {
#     reverse_proxy 127.0.0.1:8000
#     header {
#         X-Content-Type-Options "nosniff"
#         X-Frame-Options "SAMEORIGIN"
#         Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self' data:; connect-src 'self';"
#     }
# }
# Caddy auto-manages Let’s Encrypt certs.
# Environment & Secrets
# Set env vars on the server (systemd Environment= or a root-owned .env not checked into Git):
# EMAIL_FROM, EMAIL_USER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT
# Admin creds, DB path if non-default, any rate-limit overrides.
# When on HTTPS, set cookies to secure=True and keep httponly for session.
# Keep .env out of version control; ensure permissions restrict access.
# Database
# SQLite file jobs.db should live in the project root with correct permissions (writable by the app user).
# Back up the DB regularly (e.g., cron + rsync or offsite snapshot).
# Logging & Monitoring
# Use systemd journal or log to file; monitor for SMTP failures, worker errors.
# Expose /health for basic health checks (DB reachable, stats).
# Consider fail2ban or similar for repeated auth failures if exposed.
# Security Hardening
# Keep Uvicorn bound to localhost; only Nginx/Caddy exposed.
# Enforce HTTPS; redirect HTTP to HTTPS.
# Maintain security headers (already in code and proxy examples).
# Rate-limit login, subscribe, reset (already in code).
# Admin routes require admin role; avoid exposing admin URLs in public UI unless logged in as admin.
# Pre-deploy Checklist
# Run tests: python -m pytest (all 76 passing).
# Verify .env on server contains correct SMTP/admin settings.
# Start app via systemd, check systemctl status amazon-alerts.
# Validate TLS: curl -I https://alerts.yourdomain.com (check 200/headers).
# Hit /health to confirm DB connectivity.
# Tail logs for errors after first run.

####################################
# Database: Keep SQLite in the repo directory. Most free hosts persist the app disk; just ensure the volume is on a persistent disk (Render: use a persistent disk; Fly: use a volume). Back up jobs.db locally before deploy. If disk isn’t reliable, switch to a free-tier Postgres (Neon/Render free) and map tables there.