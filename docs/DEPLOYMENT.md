# Deployment Guide

This guide provides instructions for deploying the Ethical OSINT Tracker to a production environment.

## Prerequisites

- A server or cloud instance (e.g., AWS EC2, DigitalOcean Droplet, Vultr).
- A domain name (recommended).
- Docker and Docker Compose (recommended for easiest deployment).
- Or, Python 3.11+, a production-grade web server (like Gunicorn), and a reverse proxy (like Nginx).

## Option 1: Deployment with Docker (Recommended)

Using Docker is the most reliable and straightforward way to deploy the application.

### 1. Create `Dockerfile`

Create a `Dockerfile` in the project root:

```Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Export the frontend
RUN reflex export

# Command to run the app
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create `docker-compose.yml`

Create a `docker-compose.yml` file to manage the application and a reverse proxy.

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: osint_tracker_app
    restart: always
    env_file:
      - .env
    volumes:
      - ./reflex.db:/app/reflex.db  # Persist the SQLite database
    networks:
      - osint_net

  nginx:
    image: nginx:latest
    container_name: osint_tracker_nginx
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

  certbot:
    image: certbot/certbot
    container_name: osint_tracker_certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    command: certonly --webroot -w /var/www/certbot --email your-email@example.com -d your-domain.com --agree-tos --no-eff-email -n

networks:
  osint_net:
    driver: bridge
```

### 3. Create `nginx.conf`

Create an `nginx.conf` file for the reverse proxy.

```nginx
events {}

http {
    server {
        listen 80;
        server_name your-domain.com;

        location / {
            return 301 https://$host$request_uri;
        }

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

        location / {
            proxy_pass http://app:3000; # Reflex frontend runs on 3000
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location /_event {
            proxy_pass http://app:8000/_event; # Reflex backend
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```
**Note**: Replace `your-domain.com` and `your-email@example.com` with your actual domain and email.

### 4. Create `.env` File

Create a `.env` file for production secrets.

```env
# Use MySQL in production
DB_URL=mysql+pymysql://user:password@db_host/osint_tracker

# Generate a strong, random secret key
SECRET_KEY=your_super_secret_key_here

# Enable API key encryption
ENCRYPT_API_KEYS=true

# API Keys
WHOISXML_API_KEY=...
HIBP_API_KEY=...
# ... etc.
```

### 5. Deploy

1. **Initial Certbot Run**:
   ```bash
   docker-compose run --rm certbot
   ```
2. **Start Application**:
   ```bash
   docker-compose up -d
   ```
3. **Initialize Database**:
   ```bash
   docker-compose exec app python reset_admin.py
   ```

The application will be available at `https://your-domain.com`.

## Option 2: Manual Deployment (without Docker)

### 1. Prepare the Server

- SSH into your server.
- Install Python 3.11+, Git, Nginx, and other dependencies.
- Clone the repository.
- Set up a virtual environment and install `requirements.txt`.

### 2. Configure Gunicorn

Gunicorn is a production-grade WSGI server.

1. **Install Gunicorn**:
   ```bash
   pip install gunicorn
   ```
2. **Create a Gunicorn service file**:
   Create `/etc/systemd/system/osint-tracker.service`:
   ```ini
   [Unit]
   Description=Gunicorn instance to serve Ethical OSINT Tracker
   After=network.target

   [Service]
   User=your_user
   Group=www-data
   WorkingDirectory=/path/to/Ethical-OSINT-Tracker
   Environment="PATH=/path/to/Ethical-OSINT-Tracker/.venv/bin"
   ExecStart=/path/to/Ethical-OSINT-Tracker/.venv/bin/gunicorn --workers 3 --bind unix:osint-tracker.sock -m 007 app.app:app

   [Install]
   WantedBy=multi-user.target
   ```
   - Replace `your_user` and paths accordingly.

3. **Start and enable the service**:
   ```bash
   sudo systemctl start osint-tracker
   sudo systemctl enable osint-tracker
   ```

### 3. Configure Nginx

Nginx will act as a reverse proxy, serving the static frontend and forwarding API requests to Gunicorn.

1. **Export the frontend**:
   ```bash
   reflex export
   ```
   This creates a `.web` directory with the static frontend build.

2. **Create an Nginx configuration file**:
   Create `/etc/nginx/sites-available/osint-tracker`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           root /path/to/Ethical-OSINT-Tracker/.web;
           try_files $uri $uri/ /index.html;
       }

       location /_event {
           proxy_pass http://unix:/path/to/Ethical-OSINT-Tracker/osint-tracker.sock;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
       }
   }
   ```

3. **Enable the site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/osint-tracker /etc/nginx/sites-enabled
   sudo nginx -t # Test configuration
   sudo systemctl restart nginx
   ```

4. **Set up SSL with Certbot**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### 4. Final Steps

1. **Set up `.env` file** as described in the Docker section.
2. **Initialize the database**:
   ```bash
   python reset_admin.py
   ```

## Production Checklist

- [ ] **Use MySQL**: Switch from SQLite to a more robust database like MySQL or PostgreSQL.
- [ ] **Set `SECRET_KEY`**: Generate a long, random string for the `SECRET_KEY` in your `.env` file.
- [ ] **Enable API Key Encryption**: Set `ENCRYPT_API_KEYS=true` in `.env`.
- [ ] **Configure Logging**: Adjust logging levels in `rxconfig.py` for production.
- [ ] **Enable HTTPS**: Use SSL/TLS to encrypt all traffic.
- [ ] **Change Default Admin Password**: Do this immediately after the first login.
- [ ] **Backup Strategy**: Implement regular backups for your database and any uploaded files.
- [ ] **Firewall**: Configure a firewall to only allow traffic on ports 80 and 443.
- [ ] **Monitoring**: Set up monitoring for application uptime and server health.

## Updating the Application

### Docker Deployment

1. **Pull latest code**:
   ```bash
   git pull origin main
   ```
2. **Rebuild and restart**:
   ```bash
   docker-compose up -d --build
   ```
3. **Run database migrations** (if any):
   ```bash
   docker-compose exec app reflex db upgrade
   ```

### Manual Deployment

1. **Pull latest code**:
   ```bash
   git pull origin main
   ```
2. **Update dependencies**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```
3. **Run database migrations**:
   ```bash
   reflex db upgrade
   ```
4. **Re-export the frontend**:
   ```bash
   reflex export
   ```
5. **Restart the Gunicorn service**:
   ```bash
   sudo systemctl restart osint-tracker
   ```
