"""API documentation configuration for AIM using Swagger/OpenAPI."""
from __future__ import annotations

from typing import Any, Dict

SWAGGER_TEMPLATE: Dict[str, Any] = {
    "swagger": "2.0",
    "info": {
        "title": "AIM — Attendance Information Manager API",
        "description": "REST API for managing student attendance, users, roles, and reports.",
        "version": "2.0.0",
        "contact": {"email": "gagan.jain.se@gmail.com"},
    },
    "basePath": "/api",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "session": {"type": "apiKey", "in": "cookie", "name": "session"}
    },
}

SWAGGER_CONFIG: Dict[str, Any] = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs/",
}


def init_swagger(app: Any) -> None:
    """Initialize Swagger documentation for the Flask app.
    
    Flasgger is an optional dependency. If not installed, Swagger docs
    will be disabled but the application will still function normally.
    """
    try:
        from flasgger import Swagger
        Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)
    except ImportError:
        # Flasgger not installed - Swagger docs unavailable
        pass
