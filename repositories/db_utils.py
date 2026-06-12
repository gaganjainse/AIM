from __future__ import annotations

from contextlib import contextmanager

from database.db import get_db_connection


@contextmanager
def db_cursor(dictionary: bool = True):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_all(query: str, params: tuple = (), dictionary: bool = True):
    with db_cursor(dictionary=dictionary) as (_, cursor):
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_one(query: str, params: tuple = (), dictionary: bool = True):
    with db_cursor(dictionary=dictionary) as (_, cursor):
        cursor.execute(query, params)
        return cursor.fetchone()


def execute(query: str, params: tuple = (), dictionary: bool = False):
    """Execute a write query and return the affected row count.

    The old implementation returned a closed connection/cursor pair, which was
    not useful outside the helper and encouraged misuse.
    """
    with db_cursor(dictionary=dictionary) as (_, cursor):
        cursor.execute(query, params)
        return cursor.rowcount
