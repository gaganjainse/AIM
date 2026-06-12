from __future__ import annotations

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector import pooling

from config import Config

_connection_pool: pooling.MySQLConnectionPool | None = None


def _get_pool() -> pooling.MySQLConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name="aim_pool",
            pool_size=Config.DB_POOL_SIZE,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connect_timeout=5,
            autocommit=False,
        )
    return _connection_pool


def get_db_connection() -> mysql.connector.MySQLConnection:
    """Get a connection from the pool (production) or a fresh one (testing)."""
    try:
        if Config.DB_POOL_SIZE > 0:
            return _get_pool().get_connection()
    except Exception:
        pass
    return _fresh_connection()


def _fresh_connection() -> mysql.connector.MySQLConnection:
    try:
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connect_timeout=5,
            autocommit=False,
        )
    except MySQLError as e:
        raise ConnectionError(f"Database connection failed: {e}") from e
