from __future__ import annotations

from flask import Blueprint

from routes.auth import login_required
from services.search_service import search_page

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
@login_required
def search() -> str:
    return search_page()
