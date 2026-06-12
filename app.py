from __future__ import annotations

import hmac
import logging
import os
import secrets
from typing import Any

from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from repositories.system_repository import fetch_settings_map, fetch_unread_notifications
from utils.email import mail

cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"],
    enabled=True,
)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=Config.TEMPLATE_DIR,
        static_folder=Config.STATIC_DIR,
    )
    app.config.from_object(Config)
    app.config["SERVER_BOOT_ID"] = secrets.token_urlsafe(16)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)

    # ── Proxy Fix ──────────────────────────────────────────────────────────────
    trust_proxy_count = app.config.get("TRUST_PROXY_COUNT", 0)
    if trust_proxy_count:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trust_proxy_count,
            x_proto=trust_proxy_count,
            x_host=1,
            x_port=1,
        )

    # ── Extensions ─────────────────────────────────────────────────────────────
    mail.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # ── Talisman (CSP, HSTS, Secure Headers) ───────────────────────────────────
    csp = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com",
        "style-src": "'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com",
        "img-src": "'self' data:",
        "font-src": "'self' cdn.jsdelivr.net cdnjs.cloudflare.com",
        "connect-src": "'self'",
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
    }
    Talisman(
        app,
        content_security_policy=csp,
        force_https=False,  # Set True behind HTTPS load balancer
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", False),
    )

    # ── CORS (API only) ────────────────────────────────────────────────────────
    cors_origins = [o.strip() for o in Config.CORS_ORIGINS if o.strip()]
    if cors_origins:
        CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    # ── Structured Logging ──────────────────────────────────────────────────────
    _setup_logging(app)

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from api.routes import api_bp
    from routes.auth import auth_bp
    from routes.files import files_bp
    from routes.dashboard import dashboard_bp
    from routes.students import students_bp
    from routes.attendance import attendance_bp
    from routes.reports import reports_bp
    from routes.calendar import calendar_bp
    from routes.admin import admin_bp
    from routes.search import search_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(search_bp)

    # ── Security Hardening Check ───────────────────────────────────────────────
    _validate_security_config(app)

    # ── Request Hooks ──────────────────────────────────────────────────────────
    @app.before_request
    def enforce_server_boot() -> None:
        if request.endpoint in {
            "static", "auth.login", "auth.logout",
            "auth.session_status", "api.session_status",
        }:
            return
        if session.get("user_id") and session.get("server_boot_id") != app.config.get("SERVER_BOOT_ID"):
            session.clear()
            return redirect(url_for("auth.login"))

    @app.before_request
    def csrf_protect() -> None:
        if request.method == "POST":
            session_token = session.get("_csrf_token")
            form_token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
            if not session_token or not form_token or not hmac.compare_digest(session_token, form_token):
                abort(400)

    @app.after_request
    def add_security_headers(response: Any) -> Any:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        return response

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)

        def csrf_field() -> Markup:
            return Markup(f'<input type="hidden" name="csrf_token" value="{session["_csrf_token"]}">')

        try:
            settings = fetch_settings_map()
            notifications = fetch_unread_notifications(session["user_id"]) if session.get("user_id") else []
        except Exception:
            settings = {}
            notifications = []

        if "year" not in settings and "semester_name" in settings:
            settings["year"] = settings["semester_name"]
        if "semester_name" not in settings and "year" in settings:
            settings["semester_name"] = settings["year"]

        return dict(
            notifications=notifications,
            settings=settings,
            system_name=settings.get("system_name", "AIM"),
            csrf_field=csrf_field,
            csrf_token=session.get("_csrf_token", ""),
            active_theme=session.get("theme", "light"),
        )

    # ── Health Check ───────────────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    @limiter.exempt
    def health() -> tuple[dict[str, str], int]:
        try:
            from database.db import get_db_connection
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                conn.close()
        except Exception:
            app.logger.exception("Health check failed")
            return {"status": "unhealthy"}, 503
        return {"status": "ok"}, 200

    # ── Metrics Endpoint ───────────────────────────────────────────────────────
    if Config.METRICS_ENABLED:
        from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
        from prometheus_client.values import MultiProcessValue
        # Use a per-app registry to avoid duplicate registration on reload
        metrics_registry = CollectorRegistry()
        REQUEST_COUNT = Counter("aim_requests_total", "Total requests", ["method", "endpoint", "status"], registry=metrics_registry)
        REQUEST_LATENCY = Histogram("aim_request_duration_seconds", "Request latency", ["endpoint"], registry=metrics_registry)

        @app.route("/metrics")
        @limiter.exempt
        def metrics() -> tuple[str, int, dict[str, str]]:
            from flask import Response
            return Response(generate_latest(metrics_registry), mimetype=CONTENT_TYPE_LATEST)

        @app.before_request
        def _start_timer() -> None:
            from time import perf_counter
            request._start_time = perf_counter()  # type: ignore[attr-defined]

        @app.after_request
        def _record_metrics(response: Any) -> Any:
            from time import perf_counter
            start = getattr(request, "_start_time", None)
            if start is not None:
                elapsed = perf_counter() - start
                endpoint = request.endpoint or "unknown"
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=endpoint,
                    status=str(response.status_code),
                ).inc()
            return response

    return app


def _setup_logging(app: Flask) -> None:
    """Configure structured logging."""
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    ))
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)


def _validate_security_config(app: Flask) -> None:
    """Warn about insecure production settings."""
    if not app.config.get("DEBUG"):
        if not app.config.get("SESSION_COOKIE_SECURE"):
            app.logger.warning("SECURITY: SESSION_COOKIE_SECURE is False in production. Enable HTTPS!")
        if app.config.get("SECRET_KEY") in ("change-me", "dev", "secret"):
            app.logger.critical("SECURITY: Default SECRET_KEY in production! Set a strong random key.")


app = create_app()


@app.errorhandler(403)
def forbidden(_) -> tuple[str, int]:
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_) -> tuple[str, int]:
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_) -> tuple[str, int]:
    return render_template("500.html"), 500


@app.errorhandler(429)
def rate_limited(_) -> tuple[str, int]:
    return render_template("429.html"), 429


if __name__ == "__main__":
    app.run(debug=getattr(Config, "DEBUG", False), use_reloader=False, host="0.0.0.0")
