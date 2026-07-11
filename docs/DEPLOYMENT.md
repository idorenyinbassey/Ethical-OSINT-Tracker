# Deployment Guide

Production deployment instructions for Ethical OSINT Tracker (Flask).

## Prerequisites

- Python 3.11+ on the server
- A domain name (recommended)
- Nginx or another reverse proxy for HTTPS

## Option 1: Docker (Recommended)

### Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

COPY . .

# Do NOT initialise the admin at build time — it needs the ADMIN_PASSWORD secret
# and a persistent database. Run it once at deploy time instead, e.g.:
#   docker compose run --rm -e ADMIN_PASSWORD='...' app python reset_admin.py

EXPOSE 3000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "run:app"]
```

> Provide `ADMIN_PASSWORD` (first run only), `SECRET_KEY`, and
> `API_KEYS_FERNET_KEY` via the container environment / secrets — never bake them
> into the image. Keep `SECRET_KEY` and `API_KEYS_FERNET_KEY` stable across
> deploys.

### docker-compose.yml

```yaml
services:
  app:
    build: .
    container_name: osint_tracker
    restart: always
    env_file: .env
    volumes:
      - ./dev.db:/app/dev.db          # persist SQLite DB
      - ./app/uploads:/app/app/uploads
    networks:
      - osint_net

  nginx:
    image: nginx:latest
    container_name: osint_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - app
    networks:
      - osint_net

networks:
  osint_net:
    driver: bridge
```

### nginx.conf

```nginx
events {}

http {
    server {
        listen 80;
        server_name your-domain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

        client_max_body_size 16M;   # match Flask MAX_CONTENT_LENGTH

        location / {
            proxy_pass http://app:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### .env (production)

```env
DB_URL=mysql+pymysql://osint_user:password@db_host/osint_tracker
SECRET_KEY=generate-a-long-random-string-here
```

### Deploy

```bash
# First run — get TLS certificate
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot --email you@example.com \
  -d your-domain.com --agree-tos --no-eff-email -n

# Start everything
docker compose up -d
```

## Option 2: Manual (Gunicorn + Nginx)

### 1. Set up the server

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx

git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### 2. Configure environment

```bash
export DB_URL=mysql+pymysql://osint_user:password@localhost/osint_tracker
export SECRET_KEY=your-long-random-secret          # keep this stable across restarts
export API_KEYS_FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')  # generate once, keep stable
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py   # first run only; min 8 chars
```

> `SECRET_KEY` and `API_KEYS_FERNET_KEY` must stay stable across restarts —
> rotating the former logs everyone out, rotating the latter makes stored API
> keys undecryptable. The systemd unit below should load them from an
> `EnvironmentFile` so every restart uses the same values.

### 3. Create a systemd service

`/etc/systemd/system/osint-tracker.service`:

```ini
[Unit]
Description=Ethical OSINT Tracker (Flask/Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/Ethical-OSINT-Tracker
EnvironmentFile=/opt/Ethical-OSINT-Tracker/.env
ExecStart=/opt/Ethical-OSINT-Tracker/.venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/run/osint-tracker.sock \
    -m 007 \
    run:app

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now osint-tracker
```

### 4. Configure Nginx

`/etc/nginx/sites-available/osint-tracker`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 16M;

    location / {
        proxy_pass http://unix:/run/osint-tracker.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/osint-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Add HTTPS
sudo certbot --nginx -d your-domain.com
```

## Production Checklist

- [ ] Set a strong, unique `SECRET_KEY`
- [ ] Switch `DB_URL` to MySQL or PostgreSQL
- [ ] Set a strong `ADMIN_PASSWORD` at setup (no default exists); rotate it if exposed
- [ ] Set stable `SECRET_KEY` and `API_KEYS_FERNET_KEY` (never bake into the image)
- [ ] Enable HTTPS (TLS via Let's Encrypt)
- [ ] Implement API key encryption in `app/utils/crypto.py`
- [ ] Restrict `app/uploads/` directory in Nginx (no public listing)
- [ ] Set up database backups
- [ ] Configure a firewall (ports 80 and 443 only)
- [ ] Add CSRF protection (`flask-wtf`) for production

## Updating

```bash
git pull origin main
pip install -r requirements.txt --upgrade
sudo systemctl restart osint-tracker
```

If the schema changed:

```bash
alembic upgrade head
sudo systemctl restart osint-tracker
```
