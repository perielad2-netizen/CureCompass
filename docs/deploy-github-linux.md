# GitHub + Linux server deployment

## 1. Create the GitHub repository

1. On GitHub: **New repository** → name it (e.g. `curecompass`), leave it **empty** (no README, no .gitignore, no license) so your first push can be clean.
2. Note the remote URL. This project’s canonical remote is `https://github.com/perielad2-netizen/CureCompass.git` (SSH: `git@github.com:perielad2-netizen/CureCompass.git`).

## 2. Push this project from your machine

From the **repository root** (`cureCompass/`):

If you already have a local repo with commits, skip `git init` / `git add` / `git commit`. Add or fix the remote with:

```bash
git remote add origin https://github.com/perielad2-netizen/CureCompass.git
# If origin already exists:
# git remote set-url origin https://github.com/perielad2-netizen/CureCompass.git
```

First-time setup from a new folder:

```bash
git init
git add .
git status   # confirm backend/.env and frontend secrets are NOT listed
git commit -m "Initial commit: CureCompass monorepo"
git branch -M main
git remote add origin https://github.com/perielad2-netizen/CureCompass.git
git push -u origin main
```

If GitHub requires auth, use a [personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) (HTTPS) or SSH keys.

**Never commit** `backend/.env`, API keys, or database passwords. Copy from `backend/.env.example` and `frontend/.env.example` on each environment.

## 3. Linux server: clone and configure

```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv nodejs npm postgresql-client nginx
# Or use your distro’s equivalents; Node 20+ recommended for the frontend build.
```

```bash
cd /opt   # or your preferred path
sudo git clone https://github.com/perielad2-netizen/CureCompass.git
sudo chown -R $USER:$USER CureCompass
cd CureCompass
```

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
nano .env   # set DATABASE_URL, REDIS_URL, SECRET_KEY, OPENAI_API_KEY, ENVIRONMENT=production, FRONTEND_URL, SMTP_*, etc.
alembic upgrade head
```

Run the API (behind Nginx or a process manager):

```bash
# Quick test
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Production-style (example with gunicorn — add `pip install gunicorn`):

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
```

### Celery (production)

Set `ENVIRONMENT=production` in `backend/.env`. Run Redis (see `infra/docker-compose.yml` or managed Redis), then:

```bash
cd /opt/curecompass/backend
source .venv/bin/activate
celery -A app.workers.celery_app:celery_app worker -l INFO -Q curecompass
celery -A app.workers.celery_app:celery_app beat -l INFO
```

Use **systemd** units or **supervisor** so worker and beat restart on boot. Details: [ops-redis-celery.md](ops-redis-celery.md).

### Frontend

```bash
cd /opt/curecompass/frontend
cp .env.example .env.local
nano .env.local   # NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api
npm ci
npm run build
npm run start   # or: node_modules/.bin/next start -p 3000
```

For production, run Next behind Nginx (reverse proxy to `127.0.0.1:3000`) and set `NEXT_PUBLIC_API_BASE_URL` to your public API URL.

### PostgreSQL

Create a database and user, then set `DATABASE_URL` in `backend/.env` (same host/port as your Postgres instance).

## 4. Nginx: one hostname, site + `/api` (HTTP or HTTPS)

Assume the app lives at `/opt/CureCompass` (adjust paths to match your server). Gunicorn listens on `127.0.0.1:8000`, Next on `127.0.0.1:3000`. Nginx terminates port **80/443** and reverse-proxies to both.

### 4.1 Create the site config

```bash
sudo nano /etc/nginx/sites-available/curecompass
```

Paste (replace `server_name` with your **public IP** or **domain**; use both if you like):

```nginx
server {
    listen 80;
    server_name 45.63.98.209 example.com www.example.com;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

After **Let’s Encrypt**, Certbot usually adds a second `server` block for `listen 443 ssl` and redirects HTTP→HTTPS. Then use **`https://`** in `FRONTEND_URL` and `NEXT_PUBLIC_API_BASE_URL` (see below).

### 4.2 Enable the site and reload Nginx

```bash
sudo ln -sf /etc/nginx/sites-available/curecompass /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 4.3 Align environment with the public URL (important)

**Backend** — `/opt/CureCompass/backend/.env`:

- `FRONTEND_URL` must be the **origin only** (no path): e.g. `https://example.com` or `http://45.63.98.209`. Used for CORS and links; do **not** append `/he` or `/api`.

**Frontend** — `/opt/CureCompass/frontend/.env.local`:

- `NEXT_PUBLIC_API_BASE_URL` must be the browser-visible API base, e.g. `https://example.com/api` or `http://45.63.98.209/api`.

`NEXT_PUBLIC_*` variables are baked in at **build** time. After changing `.env.local`:

```bash
cd /opt/CureCompass/frontend
npm ci   # optional, if dependencies changed
npm run build
sudo systemctl restart curecompass-web
sudo systemctl restart curecompass-api
```

Backend `.env` is read when Gunicorn starts; after editing it:

```bash
sudo systemctl restart curecompass-api curecompass-worker curecompass-beat
```

### 4.4 Firewall (UFW example)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw status
```

### 4.5 Smoke test

- Site: `http://YOUR_HOST/` or `https://YOUR_HOST/`
- API docs (if enabled in production): `http://YOUR_HOST/api/docs`

---

## 5. systemd services (example unit names)

A typical production host runs four units (names may match your install):

| Service | Role |
|--------|------|
| `curecompass-api` | Gunicorn + Uvicorn workers on `127.0.0.1:8000` |
| `curecompass-web` | `next start` on `127.0.0.1:3000` |
| `curecompass-worker` | Celery worker |
| `curecompass-beat` | Celery beat |

**Status**

```bash
sudo systemctl status curecompass-api curecompass-web curecompass-worker curecompass-beat --no-pager
```

**Restart after config or code deploy**

```bash
sudo systemctl restart curecompass-api curecompass-web curecompass-worker curecompass-beat
```

**Logs (if something fails)**

```bash
sudo journalctl -u curecompass-api -u curecompass-web -n 80 --no-pager
```

### 5.1 Gunicorn: “Connection in use” on port 8000

If `systemctl restart curecompass-api` logs `Connection in use: ('127.0.0.1', 8000)`, an old Gunicorn (or another process) is still bound to **8000**.

1. Check what holds the port: `sudo ss -tlnp | grep 8000` or `sudo lsof -i :8000`.
2. Stop the API cleanly: `sudo systemctl stop curecompass-api`, wait a second, then `sudo systemctl start curecompass-api`.
3. If a stray process remains, kill it (carefully), then start the unit again.

Often a second `systemctl restart curecompass-api` after the old master exits is enough.

---

## 6. Ongoing updates

```bash
cd /opt/CureCompass
git pull
cd backend && source .venv/bin/activate && alembic upgrade head && deactivate
cd ../frontend && npm ci && npm run build
sudo systemctl restart curecompass-api curecompass-web curecompass-worker curecompass-beat
sudo nginx -t && sudo systemctl reload nginx   # only if you changed Nginx
```

If you only changed **backend** `.env`: restart `curecompass-api` (and worker/beat if they rely on the same vars). If you only changed **frontend** `NEXT_PUBLIC_*`: rebuild + restart `curecompass-web`.

---

## Optional: Docker on the server

You can extend `infra/docker-compose.yml` with API + worker + beat + Postgres images; this repo does not ship a full production Compose stack yet—add one when you standardize on containers.
