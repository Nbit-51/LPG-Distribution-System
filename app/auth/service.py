import warnings
warnings.filterwarnings("ignore", ".*error reading bcrypt version.*")

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.database import execute_query
from app.config import settings

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ALGORITHM     = "HS256"
TOKEN_EXPIRE_H = 12

def hash_password(p): return pwd_context.hash(p)
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_H)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

# ── Admin ─────────────────────────────────────────────────
def get_admin_by_username(username):
    rows = execute_query("SELECT * FROM admins WHERE username=%s AND is_active=TRUE", (username,))
    return rows[0] if rows else None

def get_admin_by_id(admin_id):
    rows = execute_query("SELECT * FROM admins WHERE admin_id=%s AND is_active=TRUE", (admin_id,))
    return rows[0] if rows else None

def authenticate_admin(username, password):
    admin = get_admin_by_username(username)
    if not admin or not verify_password(password, admin["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.")
    execute_query("UPDATE admins SET last_login=NOW() WHERE admin_id=%s", (admin["admin_id"],), fetch=False)
    return admin

def get_current_admin(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials.",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub", "")
        if sub.startswith("consumer:"):
            raise exc
        admin_id = sub
        if not admin_id:
            raise exc
    except JWTError:
        raise exc
    admin = get_admin_by_id(int(admin_id))
    if not admin:
        raise exc
    return admin

def require_superadmin(admin=Depends(get_current_admin)):
    if admin["role"] != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superadmin access required.")
    return admin

def register_admin(username, password, full_name, email, role="viewer", agency_id=None):
    if get_admin_by_username(username):
        raise ValueError(f"Username '{username}' already exists.")
    admin_id = execute_query(
        "INSERT INTO admins (username, password_hash, full_name, email, role, agency_id) VALUES (%s,%s,%s,%s,%s,%s)",
        (username, hash_password(password), full_name, email, role, agency_id), fetch=False,
    )
    return get_admin_by_id(admin_id)

# ── Consumer ──────────────────────────────────────────────
def get_consumer_by_phone_auth(phone):
    rows = execute_query("SELECT * FROM consumers WHERE phone=%s", (phone,))
    return rows[0] if rows else None

def get_consumer_by_phone_or_email_auth(phone_or_email):
    if "@" in phone_or_email:
        rows = execute_query("SELECT * FROM consumers WHERE email=%s", (phone_or_email,))
    else:
        rows = execute_query("SELECT * FROM consumers WHERE phone=%s", (phone_or_email,))
    return rows[0] if rows else None

def get_consumer_by_id_auth(consumer_id):
    rows = execute_query("SELECT * FROM consumers WHERE consumer_id=%s AND is_active=TRUE", (consumer_id,))
    return rows[0] if rows else None

def register_consumer_account(full_name, phone, address, password, consumer_type, agency_id, email=None):
    existing = execute_query("SELECT consumer_id, full_name FROM consumers WHERE phone=%s", (phone,))
    if existing:
        raise ValueError(
            f"Account with phone {phone} already exists (Name: {existing[0]['full_name']}). Please login instead."
        )
    if email:
        existing_email = execute_query("SELECT consumer_id, full_name FROM consumers WHERE email=%s", (email,))
        if existing_email:
            raise ValueError(
                f"Account with email {email} already exists (Name: {existing_email[0]['full_name']}). Please login instead."
            )
    quota_map = {"domestic": 2, "essential": 5, "commercial": 10}
    quota = quota_map.get(consumer_type, 2)
    consumer_id = execute_query(
        "INSERT INTO consumers (full_name, email, phone, address, consumer_type, cylinder_quota, agency_id, password_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (full_name, email, phone, address, consumer_type, quota, agency_id, hash_password(password)),
        fetch=False,
    )
    return get_consumer_by_id_auth(consumer_id)

def authenticate_consumer(phone_or_email, password):
    consumer = get_consumer_by_phone_or_email_auth(phone_or_email)
    if not consumer:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phone number or email not registered.")
    if not consumer.get("password_hash") or not verify_password(password, consumer["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect password.")
    if not consumer["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is deactivated.")
    return consumer

def create_consumer_token(consumer_id):
    return create_access_token({"sub": f"consumer:{consumer_id}"})

def get_current_consumer(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials.",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub", "")
        if not sub.startswith("consumer:"):
            raise exc
        consumer_id = int(sub.split(":")[1])
    except (JWTError, ValueError):
        raise exc
    consumer = get_consumer_by_id_auth(consumer_id)
    if not consumer:
        raise exc
    return consumer

def create_agent_token(agent_id):
    return create_access_token({"sub": f"agent:{agent_id}"})

def get_current_agent(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials.",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub", "")
        if not sub.startswith("agent:"):
            raise exc
        agent_id = int(sub.split(":")[1])
    except (JWTError, ValueError):
        raise exc
    from app.delivery_agents.service import get_agent_by_id
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise exc
    return agent