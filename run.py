"""Development entry point.

Do NOT use this in production — use wsgi.py with Gunicorn instead.

Usage:
    python run.py
"""
import os
from app import app

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)),
            debug=debug, use_reloader=False)
