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

## 4. Nginx (sketch)

- **API**: `proxy_pass http://127.0.0.1:8000;` with paths under `/api` (or dedicated subdomain `api.example.com`).
- **Frontend**: `proxy_pass http://127.0.0.1:3000;` for the site, or serve `next export` static output if you switch to static export later.
- Enable TLS with **Let’s Encrypt** (`certbot`).

## 5. Ongoing updates

```bash
cd /opt/curecompass
git pull
cd backend && source .venv/bin/activate && alembic upgrade head && deactivate
cd ../frontend && npm ci && npm run build
# Restart systemd services for API, worker, beat, and Next.
```

## Optional: Docker on the server

You can extend `infra/docker-compose.yml` with API + worker + beat + Postgres images; this repo does not ship a full production Compose stack yet—add one when you standardize on containers.
