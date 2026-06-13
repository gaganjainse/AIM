from __future__ import annotations

import logging
import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector import pooling

from config import Config

logger = logging.getLogger(__name__)

_connection_pool: pooling.MySQLConnectionPool | None = None
_pool_stats = {"created": 0, "failed": 0}


def _get_pool() -> pooling.MySQLConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        try:
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
            _pool_stats["created"] = 1
            logger.info("Database connection pool initialized with size=%d", Config.DB_POOL_SIZE)
        except Exception as e:
            logger.error("Failed to create connection pool: %s", e)
            _pool_stats["failed"] += 1
            raise
    return _connection_pool


def get_db_connection() -> mysql.connector.MySQLConnection:
    """Get a connection from the pool (production) or a fresh one (testing)."""
    try:
        if Config.DB_POOL_SIZE > 0:
            return _get_pool().get_connection()
    except Exception as e:
        logger.debug("Pool connection failed, using fresh connection: %s", e)
        _pool_stats["failed"] += 1
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
        logger.error("Fresh database connection failed: %s", e)
        raise ConnectionError(f"Database connection failed: {e}") from e


def get_pool_stats() -> dict:
    """Return connection pool statistics for monitoring."""
    pool = _connection_pool
    if pool:
        return {
            "pool_name": pool.pool_name,
            "pool_size": pool.pool_size,
            "pool_resized": getattr(pool, "pool_resized", False),
            "connections_created": _pool_stats["created"],
            "connections_failed": _pool_stats["failed"],
        }
    return {
        "pool_name": None,
        "pool_size": Config.DB_POOL_SIZE,
        "pool_resized": False,
        "connections_created": _pool_stats["created"],
        "connections_failed": _pool_stats["failed"],
    }
