"""WSGI entry point for production servers (Gunicorn, uWSGI, mod_wsgi).

Usage:
    gunicorn -c deploy/gunicorn.conf.py wsgi:application
"""
from __future__ import annotations

from app import app

application = app
