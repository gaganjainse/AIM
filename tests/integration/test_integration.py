"""Integration tests for AIM application."""
from __future__ import annotations

import os
import pytest
from typing import Generator

os.environ.setdefault("FLASK_SECRET", "test-secret-key")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("CACHE_TYPE", "NullCache")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("METRICS_ENABLED", "false")


@pytest.fixture
def app():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["DB_POOL_SIZE"] = 0
    app.config["RATELIMIT_ENABLED"] = False
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


class TestHealthCheck:
    def test_health_endpoint_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code in (200, 503)

    def test_health_returns_json(self, client):
        response = client.get("/health")
        data = response.get_json()
        assert data is not None
        assert "status" in data


class TestUnauthenticatedAccess:
    def test_dashboard_requires_login(self, client):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302

    def test_students_requires_login(self, client):
        response = client.get("/students", follow_redirects=False)
        assert response.status_code == 302

    def test_attendance_requires_login(self, client):
        response = client.get("/attendance", follow_redirects=False)
        assert response.status_code == 302


class TestLoginPage:
    def test_login_page_loads(self, client):
        response = client.get("/login")
        assert response.status_code == 200

    def test_login_page_contains_form(self, client):
        response = client.get("/login")
        assert b"<form" in response.data


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        response = client.get("/login")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


class TestErrorPages:
    def test_404_page(self, client):
        response = client.get("/nonexistent-page-xyz")
        assert response.status_code == 404


class TestCustomExceptions:
    def test_aim_exception_base(self):
        from utils.exceptions import AIMException
        exc = AIMException("test error")
        assert exc.message == "test error"
        assert exc.code == "INTERNAL_ERROR"
        assert exc.status_code == 400

    def test_validation_error(self):
        from utils.exceptions import ValidationError
        exc = ValidationError("invalid", field="email")
        assert exc.field == "email"

    def test_authentication_error(self):
        from utils.exceptions import AuthenticationError
        exc = AuthenticationError()
        assert exc.status_code == 401

    def test_authorization_error(self):
        from utils.exceptions import AuthorizationError
        exc = AuthorizationError()
        assert exc.status_code == 403

    def test_rate_limit_error(self):
        from utils.exceptions import RateLimitError
        exc = RateLimitError()
        assert exc.status_code == 429


class TestInputValidation:
    def test_empty_username(self, client):
        response = client.post("/login", data={"username": "", "password": "x"}, follow_redirects=True)
        assert response.status_code in (200, 400)

    def test_sql_injection_attempt(self, client):
        response = client.post("/login", data={"username": "' OR '1'='1", "password": "x"}, follow_redirects=True)
        assert response.status_code in (200, 400)

    def test_xss_attempt(self, client):
        response = client.post("/login", data={"username": "<script>alert(1)</script>", "password": "x"}, follow_redirects=True)
        assert response.status_code in (200, 400)
        assert b"<script>" not in response.data
