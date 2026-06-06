from mysql.connector import pooling, errors
import logging
import time
import contextvars
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_pool = None
# ContextVar to hold a connection for request-scoped connection reuse / transactions
_conn_var = contextvars.ContextVar("db_connection", default=None)

# Simple in-memory cache for static configurations
_static_cache = {}
_static_cache_expiry = {}

def _get_pool():
    global _pool
    if _pool is None:
        from app.config import settings
        pool_kwargs = dict(
            pool_name="lpg_pool",
            pool_size=20, # Increased pool_size from 3 to 20 for higher throughput
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            autocommit=False,
            connection_timeout=8,
            pool_reset_session=True,  # Reset session state on return
            use_pure=False,           # Disable pure Python mode for better C-based performance (falls back to pure if C extensions not present)
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

@contextmanager
def db_session(autocommit=True):
    """
    Context manager to reuse a single database connection.
    If already inside a session, reuses the existing connection.
    Otherwise, starts a new transaction/connection block.
    """
    conn = _conn_var.get()
    if conn is not None:
        # Already inside a session
        yield conn
        return

    conn = get_connection()
    token = _conn_var.set(conn)
    try:
        yield conn
        if autocommit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _conn_var.reset(token)
        try:
            conn.close()
        except Exception:
            pass

def execute_query(query, params=(), fetch=True):
    # Intercept static configuration queries to bypass DB call and reduce latency
    clean_query = " ".join(query.lower().split())
    is_cacheable = fetch and any(
        table in clean_query 
        for table in ["booking_restrictions", "priority_policies"]
    )
    
    if is_cacheable:
        cache_key = (query, tuple(params))
        now = time.time()
        if cache_key in _static_cache and now < _static_cache_expiry.get(cache_key, 0):
            return _static_cache[cache_key]

    # Check if inside an active session/transaction
    active_conn = _conn_var.get()
    if active_conn is not None:
        cursor = active_conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if fetch:
                res = cursor.fetchall()
                if is_cacheable:
                    _static_cache[cache_key] = res
                    _static_cache_expiry[cache_key] = time.time() + 30.0 # Cache for 30 seconds
                return res
            else:
                return cursor.lastrowid
        finally:
            cursor.close()
    
    # Otherwise, open a short-lived connection
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if fetch:
            res = cursor.fetchall()
            conn.commit()
            if is_cacheable:
                _static_cache[cache_key] = res
                _static_cache_expiry[cache_key] = time.time() + 30.0
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
    active_conn = _conn_var.get()
    if active_conn is not None:
        cursor = active_conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, args)
            results = []
            for rs in cursor.stored_results():
                results.extend(rs.fetchall())
            return results
        finally:
            cursor.close()

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

