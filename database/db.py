from __future__ import annotations

import logging

from config import Config

logger = logging.getLogger(__name__)

_connection_pool = None
_pool_stats = {"created": 0, "failed": 0}
_db_unavailable = False


class DatabaseUnavailableError(ConnectionError):
    pass


def _get_pool():
    global _connection_pool, _db_unavailable
    if _db_unavailable:
        raise DatabaseUnavailableError("Database is not available (demo mode)")
    if _connection_pool is None:
        try:
            import mysql.connector
            from mysql.connector import pooling
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
        except ImportError:
            _db_unavailable = True
            raise DatabaseUnavailableError("mysql-connector-python not installed (demo mode)")
        except Exception as e:
            logger.error("Failed to create connection pool: %s", e)
            _pool_stats["failed"] += 1
            if Config.DEMO:
                _db_unavailable = True
                raise DatabaseUnavailableError(f"Database not available (demo mode): {e}") from e
            raise
    return _connection_pool


def get_db_connection():
    """Get a connection from the pool."""
    if _db_unavailable:
        raise DatabaseUnavailableError("Database is not available (demo mode)")
    try:
        import mysql.connector
        if Config.DB_POOL_SIZE > 0:
            return _get_pool().get_connection()
    except DatabaseUnavailableError:
        raise
    except Exception as e:
        logger.debug("Pool connection failed, using fresh connection: %s", e)
        _pool_stats["failed"] += 1
    return _fresh_connection()


def _fresh_connection():
    try:
        import mysql.connector
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connect_timeout=5,
            autocommit=False,
        )
    except DatabaseUnavailableError:
        raise
    except Exception as e:
        logger.error("Fresh database connection failed: %s", e)
        if Config.DEMO:
            raise DatabaseUnavailableError(f"Database not available (demo mode): {e}") from e
        raise ConnectionError(f"Database connection failed: {e}") from e


def get_pool_stats() -> dict:
    """Return connection pool statistics for monitoring."""
    if _connection_pool is None:
        return {
            "pool_name": None,
            "pool_size": Config.DB_POOL_SIZE,
            "pool_resized": False,
            "connections_created": _pool_stats["created"],
            "connections_failed": _pool_stats["failed"],
        }
    return {
        "pool_name": _connection_pool.pool_name,
        "pool_size": _connection_pool.pool_size,
        "pool_resized": getattr(_connection_pool, "pool_resized", False),
        "connections_created": _pool_stats["created"],
        "connections_failed": _pool_stats["failed"],
    }
