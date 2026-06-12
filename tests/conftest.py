"""Shared test fixtures for AIM test suite."""
from __future__ import annotations

import os
import pytest
from typing import Generator

os.environ.setdefault("FLASK_SECRET", "test-secret-key-for-testing-only")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("CACHE_TYPE", "NullCache")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("METRICS_ENABLED", "false")


def _db_available() -> bool:
    """Check if MySQL is available for integration tests."""
    try:
        from database.db import get_db_connection
        conn = get_db_connection()
        conn.close()
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_available()


@pytest.fixture
def app() -> Generator:
    """Create application for testing."""
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["DB_POOL_SIZE"] = 0
    app.config["RATELIMIT_ENABLED"] = False
    app.config["SERVER_BOOT_ID"] = "test-boot-id"
    with app.app_context():
        yield app


@pytest.fixture
def client(app) -> Generator:
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(app) -> Generator:
    """Create authenticated test client (requires DB)."""
    if not DB_AVAILABLE:
        pytest.skip("MySQL not available")
    with app.test_client() as client:
        with app.app_context():
            from werkzeug.security import generate_password_hash
            from repositories.db_utils import db_cursor
            with db_cursor(dictionary=False) as (_, cursor):
                cursor.execute(
                    "INSERT IGNORE INTO users (id, username, password, email, email_notifications, theme, records_per_page) "
                    "VALUES (999, 'testadmin', %s, 'test@test.com', 1, 'light', 10)",
                    (generate_password_hash("TestPass1!"),)
                )
                cursor.execute("INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (999, 1)")
                cursor.execute("INSERT IGNORE INTO user_notification_settings (user_id) VALUES (999)")
        client.post("/login", data={
            "username": "testadmin",
            "password": "TestPass1!",
        }, follow_redirects=True)
        yield client


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "integration: mark test as requiring database")
