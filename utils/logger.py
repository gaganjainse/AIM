from __future__ import annotations

from functools import lru_cache
from typing import Any

from repositories.db_utils import db_cursor


def _get_log_connection() -> Any:
    """Get a separate database connection for logging (won't interfere with main transaction)."""
    from database.db import get_db_connection
    return get_db_connection()


@lru_cache(maxsize=1)
def _log_columns() -> set[str]:
    try:
        with db_cursor(dictionary=False) as (_, cursor):
            cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = 'logs'
                """
            )
            columns = {row[0] for row in cursor.fetchall()}
        return columns
    except Exception:
        return {"user_id", "action", "ip_address", "time"}


def _build_log_insert(
    action: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    target_table: str | None = None,
    target_id: int | None = None,
) -> tuple[str | None, tuple | None]:
    """Build log INSERT statement using whitelisted column names.
    
    This approach prevents SQL injection by only allowing known safe column names
    from the logs table schema. All values are parameterized.
    """
    columns = _log_columns()
    # Whitelist of allowed column names to prevent SQL injection
    ALLOWED_LOG_FIELDS = {
        "user_id", "action", "target_table", "target_id", 
        "ip_address", "time"
    }
    fields: list[str] = []
    values: list[Any] = []

    if "user_id" in columns:
        fields.append("user_id")
        values.append(user_id)
    if "action" in columns:
        fields.append("action")
        values.append(action)
    if "target_table" in columns and target_table is not None:
        fields.append("target_table")
        values.append(target_table)
    if "target_id" in columns and target_id is not None:
        fields.append("target_id")
        values.append(target_id)
    if "ip_address" in columns:
        fields.append("ip_address")
        values.append(ip_address)

    if not fields:
        return None, None

    # Filter fields through whitelist for extra safety
    # nosec B608 - Fields are whitelisted from schema introspection and validated
    safe_fields = [f for f in fields if f in ALLOWED_LOG_FIELDS]
    placeholders = ", ".join(["%s"] * len(safe_fields))
    sql = f"INSERT INTO logs ({', '.join(safe_fields)}) VALUES ({placeholders})"
    return sql, tuple(values)


def log_action_on_cursor(
    cursor,
    action: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    target_table: str | None = None,
    target_id: int | None = None,
) -> bool:
    try:
        sql, values = _build_log_insert(action, user_id=user_id, ip_address=ip_address, target_table=target_table, target_id=target_id)
        if not sql:
            return False
        cursor.execute(sql, values)
        return True
    except Exception:
        return False


def log_action(
    action: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    target_table: str | None = None,
    target_id: int | None = None,
) -> bool:
    try:
        sql, values = _build_log_insert(action, user_id=user_id, ip_address=ip_address, target_table=target_table, target_id=target_id)
        if not sql:
            return False
        conn = _get_log_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False
