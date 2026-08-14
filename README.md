# AIM — Attendance Information Manager

A robust, production-ready attendance management system built with **Flask + MySQL**:
layered architecture, Argon2id auth, CSRF/JWT security, Prometheus monitoring, and a
full CI/CD pipeline.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-101-success?style=for-the-badge)
![CI](https://github.com/gaganjainse/AIM/actions/workflows/ci.yml/badge.svg)

## Quick start

```bash
# Local (venv)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask run                       # set DB_* + FLASK_SECRET env vars

# Docker Compose (MySQL included)
docker compose up --build
```

Demo: [aim-live.vercel.app](https://aim-live.vercel.app) (landing page — the full app
needs MySQL, see `render.yaml` for one-click Render deploy).

## Features

- **Layered architecture** — routes → services → repositories → models
- **Auth & security** — Argon2id hashing (OWASP), CSRF protection, brute-force lockout, breached-password detection (HaveIBeenPwned k-anonymity), rate limiting
- **Hardened headers** — Flask-Talisman (CSP/HSTS), Flask-CORS
- **Attendance & admin** — student management, reports (Chart.js), scheduling (FullCalendar), CSV import/export, light/dark themes
- **Observability** — Prometheus metrics endpoint, structured JSON logging, health checks
- **Testing** — 101 pytest tests across 7 files
- **Deployment** — Docker Compose (multi-stage build, MySQL healthcheck), Gunicorn, Nginx
- **CI/CD** — GitHub Actions: Bandit (documented exclusions), pip-audit (keyless), Flake8, py_compile, Pytest
- **Accessibility** — WCAG 2.1 AA, ARIA live regions, semantic HTML, keyboard navigation
- **Encrypted backups** — backup/restore with integrity checks

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, Flask, Gunicorn, Nginx |
| Database | MySQL 8 |
| Frontend | Jinja2, Bootstrap 5, Chart.js, FullCalendar |
| Security | Argon2id, Flask-Talisman, Flask-CORS, Flask-Limiter |
| DevOps | Docker Compose, GitHub Actions, Render (`render.yaml`) |
| Testing | pytest, Bandit, pip-audit, Flake8 |

## Development

```bash
pytest tests/ -q                        # 101 tests
flake8 . --select=E9,F63,F7,F82          # critical lint
bandit -r . -c bandit.yaml -ll           # documented exclusions
pip-audit -r requirements.txt            # dependency vulnerabilities
```

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
## 📚 Docs

Fleet-wide reading compilation: [shesh-docs](https://github.com/gaganjainse/shesh-docs).
