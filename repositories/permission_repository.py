from __future__ import annotations

from repositories.db_utils import db_cursor


def user_has_permission(user_id: int, permission_name: str) -> bool:
    with db_cursor(dictionary=True) as (_, cursor):
        cursor.execute(
            """
            SELECT 1
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id=%s AND p.permission_name=%s
            LIMIT 1
            """,
            (user_id, permission_name),
        )
        row = cursor.fetchone()
    return row is not None
