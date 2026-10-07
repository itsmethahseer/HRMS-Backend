from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import bcrypt
from jose import jwt
from app.core.config import settings

# In-memory token blacklist for logout (use Redis in production)
_token_blacklist: set = set()
# In-memory reset tokens store: {token: (schema_name, user_id, expiry)}
_reset_tokens: dict = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire, 
        "type": "access",
        "jti": secrets.token_urlsafe(16)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def blacklist_token(token: str) -> None:
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    return token in _token_blacklist


def generate_password_reset_token(schema_name: str, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    _reset_tokens[token] = {"schema_name": schema_name, "user_id": user_id, "expiry": expiry}
    return token


def verify_password_reset_token(token: str) -> Optional[dict]:
    data = _reset_tokens.get(token)
    if not data:
        return None
    if datetime.now(timezone.utc) > data["expiry"]:
        _reset_tokens.pop(token, None)
        return None
    return data


def consume_password_reset_token(token: str) -> None:
    _reset_tokens.pop(token, None)

