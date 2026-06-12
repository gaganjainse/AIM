# AIM Deployment Guide

This guide is written so you can hand the project to someone else and they can run, verify, and deploy it without guessing.

## 1. What is already included

- Flask application entrypoints: `app.py`, `run.py`, `wsgi.py`
- Dependency list: `requirements.txt`
- Database schema: `schema.sql`
- Docker deployment files: `Dockerfile`, `docker-compose.yml`, `deploy/nginx.docker.conf`
- Linux production files: `deploy/gunicorn.conf.py`, `deploy/nginx.conf`, `deploy/aim.service`
- Environment example: `.env.example`
- Demo data seeder: `demo/seed_demo_data.py`
- Test suite: `tests/` (84 tests)
- CI/CD pipeline: `.github/workflows/ci.yml`

## 2. Required environment values

Create a `.env` file in the project root by copying `.env.example` and updating the values below:

```env
FLASK_SECRET=replace-with-a-long-random-secret
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=replace-with-your-db-password
DB_NAME=attendance_db
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=1
SESSION_COOKIE_NAME=aim_session
MAX_CONTENT_LENGTH_MB=10
TRUST_PROXY_COUNT=1
MYSQL_BIN=mysql
MYSQLDUMP_BIN=mysqldump
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_TLS=1
EMAIL_USER=
EMAIL_PASS=

# New in v2.0
DB_POOL_SIZE=5
ARGON2_TIME_COST=2
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=4
RATELIMIT_DEFAULT=200 per day, 50 per hour
CORS_ORIGINS=
BACKUP_ENCRYPTION_KEY=
CACHE_TYPE=SimpleCache
METRICS_ENABLED=true
```

Notes:

- Set `SESSION_COOKIE_SECURE=0` for plain HTTP local testing.
- Set `DB_HOST=db` when using Docker Compose.
- Keep `FLASK_DEBUG=0` in production.
- Fill email settings only if you want mail features active.
- Generate `FLASK_SECRET` with: `python -c "import secrets; print(secrets.token_hex())"`
- Generate `BACKUP_ENCRYPTION_KEY` with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## 3. Local setup on Windows

Run these commands from the project root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Create the MySQL database, then load the schema:

```powershell
mysql -u root -p -e "CREATE DATABASE attendance_db;"
mysql -u root -p attendance_db < database/schema.sql
```

Seed demo data:

```powershell
python demo/seed_demo_data.py
```

Start the app:

```powershell
python run.py
```

Open:

- `http://127.0.0.1:5000`

Default login: `admin` / `admin123!`

## 4. Fastest deployment path with Docker

This is the fastest option if you want something deployable with the least manual setup.

1. Copy `.env.example` to `.env`.
2. Change at least: `FLASK_SECRET`, `DB_PASSWORD`, `SESSION_COOKIE_SECURE=1`
3. Build and start:

```powershell
docker compose up --build -d
```

What starts:

- `db`: MySQL 8.4
- `app`: Flask app served with Gunicorn
- `nginx`: reverse proxy serving the app on port `80` (Docker-specific Nginx config)

Seed demo data:

```powershell
docker compose exec app python demo/seed_demo_data.py
```

Open:

- `http://YOUR_SERVER_IP/`

Useful Docker commands:

```powershell
docker compose logs -f
docker compose ps
docker compose restart
docker compose down
```

## 5. Linux VPS deployment with Gunicorn + Nginx

Use this for a traditional VM or cloud server deployment.

### Step 1: copy the project

Place the project in:

- `/opt/aim`

### Step 2: install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx mysql-client
```

Install and configure MySQL separately if it is on the same server.

### Step 3: create the Python environment

```bash
cd /opt/aim
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with production values.

### Step 4: prepare the database

```bash
mysql -u root -p -e "CREATE DATABASE attendance_db;"
mysql -u root -p attendance_db < database/schema.sql
```

### Step 5: seed demo data

```bash
python demo/seed_demo_data.py
```

### Step 6: install systemd service

```bash
sudo cp deploy/aim.service /etc/systemd/system/aim.service
sudo systemctl daemon-reload
sudo systemctl enable aim
sudo systemctl start aim
sudo systemctl status aim
```

### Step 7: install Nginx site

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/default.conf
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: verify

Check:

- `http://YOUR_DOMAIN_OR_IP/`
- `sudo journalctl -u aim -f`
- `sudo nginx -t`

## 6. Pre-deployment checklist

Before going live, confirm all of these:

- `.env` exists and has the correct database credentials
- `FLASK_SECRET` is unique and strong (generate with `secrets.token_hex()`)
- `SESSION_COOKIE_SECURE=1` for HTTPS deployments
- MySQL database is created
- `schema.sql` is imported
- `backups/` and `data/` folders are writable
- Static files load correctly
- Login works
- Attendance save works
- CSV import works
- Theme switching works in both light and dark mode
- Security headers present (check with browser dev tools)
- Rate limiting active
- `/health` endpoint returns 200
- `/metrics` endpoint returns Prometheus data

## 7. Smoke test after deployment

After deployment, test this flow in order:

1. Open the login page.
2. Sign in with a valid account.
3. Switch between light mode and dark mode.
4. Open `Students` and confirm tables and modals load correctly.
5. Open `Attendance`, change the date, and confirm dropdown colors match the theme.
6. Save attendance for at least one date.
7. Open `Reports` and `Dashboard`.
8. Download a sample CSV and verify imports work.
9. Open `Backup & Restore` if your role allows it.
10. Check `/health` returns `{"status": "ok"}`.
11. Check `/metrics` returns Prometheus data.
12. Verify security headers in browser dev tools (CSP, HSTS, etc.).

## 8. Troubleshooting

If the app does not start:

- Check `.env` values first.
- Confirm MySQL is reachable from the app host.
- Confirm the schema was imported.
- Run `pip install -r requirements.txt` again inside the active environment.

If CSS or JS looks stale:

- Hard refresh the browser.
- Restart the app container or Gunicorn service.
- Confirm Nginx is serving `/static/` from this project.

If Docker app logs show database connection errors:

- Make sure the Docker Compose file is overriding `DB_HOST` to `db` for the app container.
- Make sure the MySQL container is healthy.

If production login loops back to the login page:

- Check `SESSION_COOKIE_SECURE`.
- If you are testing over plain HTTP, use `SESSION_COOKIE_SECURE=0`.
- If behind a proxy, keep `TRUST_PROXY_COUNT=1`.

## 9. Files to share with a deployment person

If you need to hand this over, send them:

- the full project folder
- `.env` or a filled deployment copy
- database access details
- preferred deployment method: Docker or Linux VPS
- this file: `docs/DEPLOYMENT_GUIDE.md`
