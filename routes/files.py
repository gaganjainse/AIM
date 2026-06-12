from __future__ import annotations

from flask import Blueprint, abort, current_app, send_from_directory
from werkzeug.utils import secure_filename

from routes.auth import login_required

files_bp = Blueprint("files", __name__, url_prefix="/files")

_ALLOWED_SAMPLE_FILES = {
    "sample_students.csv",
    "sample_attendance.csv",
}


@files_bp.route("/sample/<path:filename>")
@login_required
def sample_file(filename: str) -> str:
    safe_name = secure_filename(filename)
    if safe_name not in _ALLOWED_SAMPLE_FILES:
        abort(404)
    return send_from_directory(
        current_app.config["DATA_DIR"],
        safe_name,
        as_attachment=True,
        download_name=safe_name,
    )
