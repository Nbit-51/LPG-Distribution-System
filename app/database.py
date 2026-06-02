from mysql.connector import pooling, errors
import logging
import time

logger = logging.getLogger(__name__)

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        from app.config import settings
        pool_kwargs = dict(
            pool_name="lpg_pool",
            pool_size=3,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            autocommit=False,
            connection_timeout=8,
            pool_reset_session=False,
            use_pure=True,
        )
        # Enable SSL for cloud databases (non-localhost)
        if settings.db_host not in ("localhost", "127.0.0.1"):
            pool_kwargs["ssl_disabled"] = False
        _pool = pooling.MySQLConnectionPool(**pool_kwargs)
    return _pool

def get_connection():
    """Get a pooled connection with automatic retry on stale connections."""
    try:
        conn = _get_pool().get_connection()
        conn.ping(reconnect=True, attempts=2, delay=1)
        return conn
    except (errors.PoolError, errors.InterfaceError):
        # Pool exhausted or stale — reset and retry
        global _pool
        _pool = None
        return _get_pool().get_connection()

def execute_query(query, params=(), fetch=True):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if fetch:
            res = cursor.fetchall()
            conn.commit()
            return res
        else:
            conn.commit()
            return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def call_procedure(proc_name, args=()):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc(proc_name, args)
        conn.commit()
        results = []
        for rs in cursor.stored_results():
            results.extend(rs.fetchall())
        return results
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def health_check():
    """Quick DB connectivity test — used for keep-alive pings."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False
