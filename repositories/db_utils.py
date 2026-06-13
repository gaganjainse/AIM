from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from database.db import get_db_connection

# Query cache for frequently executed read queries
_query_cache: dict[str, list[dict[str, Any]]] = {}
_cache_enabled = True


def enable_query_cache() -> None:
    """Enable query caching."""
    global _cache_enabled
    _cache_enabled = True


def disable_query_cache() -> None:
    """Disable query caching."""
    global _cache_enabled
    _cache_enabled = True


def clear_query_cache() -> None:
    """Clear all cached queries."""
    _query_cache.clear()


@contextmanager
def db_cursor(dictionary: bool = True, use_cache: bool = False):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        conn.commit()
        if use_cache:
            clear_query_cache()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_all(query: str, params: tuple = (), dictionary: bool = True, use_cache: bool = False):
    """Fetch all rows from a query.
    
    Args:
        query: SQL query string
        params: Query parameters
        dictionary: Return results as dictionaries
        use_cache: Cache the result for subsequent calls (read-only queries only)
    """
    cache_key = None
    if use_cache and _cache_enabled:
        cache_key = f"{query}:{params}:{dictionary}"
        if cache_key in _query_cache:
            return _query_cache[cache_key]
    
    with db_cursor(dictionary=dictionary) as (_, cursor):
        cursor.execute(query, params)
        result = cursor.fetchall()
    
    if cache_key is not None:
        _query_cache[cache_key] = result
    
    return result


def fetch_one(query: str, params: tuple = (), dictionary: bool = True, use_cache: bool = False):
    """Fetch a single row from a query.
    
    Args:
        query: SQL query string
        params: Query parameters
        dictionary: Return result as dictionary
        use_cache: Cache the result for subsequent calls (read-only queries only)
    """
    cache_key = None
    if use_cache and _cache_enabled:
        cache_key = f"{query}:{params}:{dictionary}"
        if cache_key in _query_cache:
            return _query_cache[cache_key][0] if _query_cache[cache_key] else None
    
    with db_cursor(dictionary=dictionary) as (_, cursor):
        cursor.execute(query, params)
        result = cursor.fetchone()
    
    if cache_key is not None:
        _query_cache[cache_key] = [result] if result else []
    
    return result


def execute(query: str, params: tuple = (), dictionary: bool = False):
    """Execute a write query and return the affected row count.

    The old implementation returned a closed connection/cursor pair, which was
    not useful outside the helper and encouraged misuse.
    """
    with db_cursor(dictionary=dictionary, use_cache=True) as (_, cursor):
        cursor.execute(query, params)
        return cursor.rowcount
