from __future__ import annotations

from flask import Blueprint, render_template

from routes.auth import login_required
from services.dashboard_service import dashboard_page

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def home() -> str:
    return render_template("home.html", page_title="Home")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard() -> str:
    return dashboard_page()
