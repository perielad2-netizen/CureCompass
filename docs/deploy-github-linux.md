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
- API health (via Nginx): `http://YOUR_HOST/api/health` — should return JSON `{"status":"ok",...}`.
- Swagger UI is at **`/docs`** on the Gunicorn app only (e.g. `http://127.0.0.1:8000/docs`), not under `/api`. A typical Nginx setup that only proxies `location /api` does **not** expose `/docs` on the public hostname unless you add a separate `location` (often omitted in production for security).

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

## 6. Ongoing updates (hardened release procedure)

Use this procedure for production code updates under `/opt/CureCompass`. It exists to prevent the **2026-10-16** outage where a deploy shell used `umask 077` before `git merge --ff-only`, leaving updated Python files as `root:root` mode `600` so the `curecompass` service account could not read them (`PermissionError` on `app/core/config.py`).

### 6.1 Hard rules

- **Git checkout umask:** use `umask 022` for `fetch` / `merge` / `pull` so tracked source files are world-readable (`644` / `755`), not `600`.
- **Secrets stay private separately:** keep `backend/.env`, `frontend/.env.local`, backup tarballs, and similar secrets at `600` (owner-only). Do **not** rely on a restrictive shell umask to protect them during Git operations.
- **Preserve ownership and permissions:** do **not** run recursive `chmod -R` or `chown -R` on the tree after pull.
- **No blind cleanup:** never run `git clean -fdx`, `git reset --hard`, or similar unless a named rollback plan explicitly requires it and untracked production files (`.env`, uploads, local overrides) are backed up and listed first.
- **Preserve untracked production files:** `.env`, uploads, venv, and local config must remain untouched by Git.
- **Never print secrets** in shell history dumps, journal snippets pasted to tickets, or preflight logs (no `cat .env`, no `printenv` of API keys).
- **Restart only affected CureCompass units.** Do **not** restart PickWise, FashionRise, synagogue, or unrelated host services.
- **Do not migrate or rebuild by default.** Run Alembic / frontend build only when that release explicitly requires it.

### 6.2 Identify the service account (do not assume)

```bash
# Prefer the User= from the API unit (typical: curecompass)
systemctl show curecompass-api -p User --value
# Cross-check worker/beat if needed:
systemctl show curecompass-worker -p User --value
systemctl show curecompass-beat -p User --value
```

Export it for the rest of the session:

```bash
export CC_SERVICE_USER="$(systemctl show curecompass-api -p User --value)"
# Fallback only if units omit User= and you have confirmed the account:
# export CC_SERVICE_USER=curecompass
test -n "$CC_SERVICE_USER"
```

### 6.3 Pre-update snapshot (read-only where possible)

```bash
cd /opt/CureCompass
git rev-parse HEAD
git status --short   # expect untracked .env / local files; do not delete them
sudo systemctl is-active curecompass-api curecompass-worker curecompass-beat
# Optional read-only helper (makes zero filesystem/process changes; -B avoids .pyc):
sudo -u "$CC_SERVICE_USER" env PYTHONDONTWRITEBYTECODE=1 \
  /opt/CureCompass/backend/.venv/bin/python -B \
  /opt/CureCompass/backend/scripts/release_preflight.py
```

The script must run **as the service account** and must not write files.

### 6.4 Fetch and fast-forward with umask 022

```bash
cd /opt/CureCompass
umask 022
git fetch origin
# Prefer an explicit SHA for production releases:
git merge --ff-only <TARGET_SHA>
# Or, only when intentionally tracking a branch tip:
# git merge --ff-only origin/main
git rev-parse HEAD
```

If the merge is not a fast-forward, **stop**. Do not force-reset. Resolve on a maintenance branch / PR first.

### 6.5 Verify changed Python file readability (service account)

List files changed by the update (example: previous HEAD `OLD_SHA` → `HEAD`):

```bash
OLD_SHA=<previous_sha>
git diff --name-only "$OLD_SHA" HEAD -- '*.py'
```

For each changed `.py` path (or run the preflight script), confirm the **service account** can read it. Example for one file:

```bash
sudo -u "$CC_SERVICE_USER" test -r /opt/CureCompass/backend/app/core/config.py
# Expect exit 0. If not: fix that file's mode/ownership individually — never chmod -R.
ls -l /opt/CureCompass/backend/app/core/config.py
# Healthy tracked source: typically owner-readable and group/other-readable (e.g. 644),
# owned consistently with the rest of the tree. Mode 600 owned by root is the failure mode from 2026-10-16.
```

**If readability fails:** restore only the affected paths (e.g. `chmod 644` on those specific files, or re-checkout those paths under `umask 022`). Do **not** recursively re-own the tree. Re-run the service-account read checks before continuing.

### 6.6 Offline import / config checks AS the service account (before restart)

These checks must **not** call OpenAI / SMTP / DB / Redis clients for I/O, must **not** print secret values, and must run as `$CC_SERVICE_USER`. Use `python -B` (or `PYTHONDONTWRITEBYTECODE=1`) so imports do not write `.pyc` files.

Application config is the module-level object `settings` from `app.core.config` — there is **no** `get_settings()`.

Preferred (read-only helper; checks `app/**/*.py` readability, then imports API + Celery entrypoints):

```bash
sudo -u "$CC_SERVICE_USER" env PYTHONDONTWRITEBYTECODE=1 \
  /opt/CureCompass/backend/.venv/bin/python -B \
  /opt/CureCompass/backend/scripts/release_preflight.py
# Optionally limit readability checks to files changed since the previous deploy SHA:
#   ... release_preflight.py --since "$OLD_SHA"
```

Manual equivalent (names only; never `cat` `.env`):

```bash
sudo -u "$CC_SERVICE_USER" bash -lc '
  set -euo pipefail
  cd /opt/CureCompass/backend
  source .venv/bin/activate
  export PYTHONDONTWRITEBYTECODE=1
  python -B -c "from app.core.config import settings; print(\"config_ok\", settings.openai_responses_model, settings.openai_reasoning_effort)"
  python -B -c "from app.main import app; print(\"app_import_ok\", app.title)"
  python -B -c "from app.workers.celery_app import celery_app; print(\"celery_import_ok\", celery_app.main)"
'
```

Fix any readability / import failure **before** restarting units.

### 6.7 Restart only affected CureCompass services

Backend-only release (typical for model / Python changes; **no** frontend rebuild):

```bash
sudo systemctl restart curecompass-api curecompass-worker curecompass-beat
```

Frontend-only release (after an explicit `npm ci` + `npm run build` when that release requires it):

```bash
sudo systemctl restart curecompass-web
```

Env-only backend change: restart `curecompass-api` and, if the same vars apply, `curecompass-worker` / `curecompass-beat`.

Do **not** restart unrelated host services.

### 6.8 Bounded health retries

Verified production health path on Gunicorn is **`/api/health`** (router prefix `/api` + route `/health`). Do **not** probe `/health` on port 8000 — that path is not mounted.

```bash
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/api/health}"
health_ok=0
for i in 1 2 3 4 5; do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null; then
    echo "health_ok attempt=$i url=$HEALTH_URL"
    health_ok=1
    break
  fi
  echo "health_retry attempt=$i"
  sleep 3
done
if [ "$health_ok" -ne 1 ]; then
  echo "health_failed after 5 attempts url=$HEALTH_URL" >&2
  exit 1
fi

sudo systemctl is-active curecompass-api curecompass-worker curecompass-beat
sudo systemctl show curecompass-api curecompass-worker curecompass-beat -p NRestarts --no-pager
```

Expect units `active` and restart counters stable after recovery. Prefer the loopback Gunicorn URL above so Nginx/TLS is not required for the gate. (Public Nginx path is the same `/api/health` on the site origin.)

### 6.9 Failure diagnosis (no secrets)

```bash
sudo systemctl status curecompass-api curecompass-worker curecompass-beat --no-pager
sudo journalctl -u curecompass-api -u curecompass-worker -u curecompass-beat -n 80 --no-pager
# Look for PermissionError / ImportError on app.core.config — do not paste .env contents.
ls -l backend/app/core/config.py
sudo -u "$CC_SERVICE_USER" test -r backend/app/core/config.py || echo "UNREADABLE_BY_SERVICE_USER"
```

### 6.10 Rollback (preserve untracked files)

`git merge --ff-only <GOOD_SHA>` **cannot** move HEAD backward to an ancestor. Fast-forward only advances when the target is a descendant of `HEAD`. Use one of the guarded procedures below instead.

**A. Git code rollback to a known-good commit** (restores tracked tree; keeps untracked secrets/data):

```bash
cd /opt/CureCompass
BAD_SHA="$(git rev-parse HEAD)"
GOOD_SHA="<known_good_sha>"   # e.g. last healthy production deploy
git rev-parse --verify "${GOOD_SHA}^{commit}"
git log --oneline "$GOOD_SHA".."$BAD_SHA"   # review what you are leaving

# Confirm untracked production files you must keep:
git status --short   # expect .env / uploads / local overrides — do not delete them

umask 022
# Detached checkout of the good commit updates tracked files only.
# It does NOT remove untracked files. Do not add -f unless you have a named conflict plan.
# Never run git clean or git reset --hard for this rollback.
git switch --detach "$GOOD_SHA"
# Older Git: git checkout --detach "$GOOD_SHA"

git rev-parse HEAD   # must equal GOOD_SHA
```

Then re-run §6.5–§6.8 as the service account and restart **only** the affected CureCompass units.

To return to branch tracking later (separate maintenance step): merge or redeploy a fixed commit via the normal §6.4 ff-only forward path — do not invent a backward ff-only.

**B. Model-only configuration rollback** (no Git move; while `gpt-4.1-mini` remains available):

1. Edit `backend/.env` carefully: set `OPENAI_RESPONSES_MODEL=gpt-4.1-mini` (do not log or `cat` the file).
2. Restart only `curecompass-api`, `curecompass-worker`, `curecompass-beat`.
3. See [OPENAI_MODEL_MIGRATION.md](OPENAI_MODEL_MIGRATION.md).

Keep **A** and **B** distinct: code SHA rollback vs env model override.

### 6.11 Migrations and frontend (only when required)

```bash
# Backend schema — only if the release notes say so:
cd /opt/CureCompass/backend && source .venv/bin/activate && alembic upgrade head && deactivate

# Frontend — only if the release includes UI changes:
cd /opt/CureCompass/frontend && npm ci && npm run build
sudo systemctl restart curecompass-web
```

Nginx reload only if you changed Nginx config: `sudo nginx -t && sudo systemctl reload nginx`.

---

## Optional: Docker on the server

You can extend `infra/docker-compose.yml` with API + worker + beat + Postgres images; this repo does not ship a full production Compose stack yet—add one when you standardize on containers.
