# Production Notes

- Root `.env.example` is the canonical environment template — copy to `.env` and fill in your values.
- `deploy/nginx.conf` is for host-based Gunicorn + Nginx deployments.
- `deploy/nginx.docker.conf` is for Docker Compose deployments.
- The app health endpoint is `/health` — returns `{"status": "ok"}` (200) or `{"status": "unhealthy"}` (503).
- The metrics endpoint is `/metrics` — Prometheus format, auto-disabled when `METRICS_ENABLED=false`.
- Docker Compose overrides `DB_HOST` to `db` inside the app container.
- Default admin credentials: `admin` / `admin123!` — **change immediately in production**.

## Security Configuration

- **SESSION_COOKIE_SECURE**: Set to `true` in production (requires HTTPS). Defaults to `false` for local dev.
- **FLASK_SECRET**: Must be a long random string. Generate with: `python -c "import secrets; print(secrets.token_hex())"`
- **BACKUP_ENCRYPTION_KEY**: Optional. If set, backups are encrypted with Fernet (AES-128-CBC). Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- **ARGON2_TIME_COST / ARGON2_MEMORY_COST / ARGON2_PARALLELISM**: Tune Argon2id hashing. Defaults are balanced for most servers.
- **RATELIMIT_DEFAULT**: Global rate limit string. Default: `200 per day, 50 per hour`.
- **CORS_ORIGINS**: Comma-separated allowed origins for API routes. Empty = no CORS.

## Performance

- **DB_POOL_SIZE**: MySQL connection pool size. Default: `5`. Increase for high-traffic deployments.
- **CACHE_TYPE**: `SimpleCache` (default, in-memory) or `RedisCache` (set `CACHE_REDIS_URL`).
- **CACHE_DEFAULT_TIMEOUT**: Cache TTL in seconds. Default: `300` (5 minutes).

## First-Time Setup

```bash
# 1. Copy and edit environment
cp .env.example .env
# Edit .env with your DB_PASSWORD, FLASK_SECRET, etc.

# 2. Start the stack
docker compose up --build -d

# 3. Seed demo data
docker compose exec app python demo/seed_demo_data.py

# 4. Access the app
# http://localhost (Docker) or http://127.0.0.1:5000 (local)
```
