"""Gunicorn production configuration for AIM.

Reference: https://docs.gunicorn.org/en/stable/settings.html
"""
import multiprocessing

# ── Binding ──────────────────────────────────────────────────────────────────
bind = "0.0.0.0:8000"

# ── Workers ───────────────────────────────────────────────────────────────────
# sync workers are the right choice for a DB-bound Flask app with no async I/O.
worker_class = "sync"
# NOTE: Gunicorn is Linux-only. On Windows, use desktop_launcher.py (waitress) instead.
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
threads = 2

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = 120
graceful_timeout = 30
keepalive = 5

# ── Performance ───────────────────────────────────────────────────────────────
# Use /dev/shm for worker heartbeat — faster than disk I/O.
worker_tmp_dir = "/dev/shm"

# Load the application before forking workers — saves memory via copy-on-write.
preload_app = True

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"        # stdout → captured by Docker / systemd
errorlog  = "-"        # stderr
loglevel  = "info"
capture_output = True
access_log_format = '%(h)s "%(r)s" %(s)s %(b)sB %(D)sµs'

# ── Limits ────────────────────────────────────────────────────────────────────
limit_request_line   = 4096
limit_request_fields = 100
