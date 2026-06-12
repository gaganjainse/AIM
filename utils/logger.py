from __future__ import annotations

import hashlib
import hmac
import hmac as hmac_mod
import os
from datetime import datetime
from functools import lru_cache
from typing import Any

from repositories.db_utils import db_cursor


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
    columns = _log_columns()
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

    placeholders = ", ".join(["%s"] * len(fields))
    sql = f"INSERT INTO logs ({', '.join(fields)}) VALUES ({placeholders})"
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False
