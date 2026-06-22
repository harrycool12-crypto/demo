import hashlib
import hmac
import os
import base64
import secrets

# In-memory session store: token -> username
_SESSIONS: dict[str, str] = {}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        raw  = base64.b64decode(hashed)
        salt, key = raw[:16], raw[16:]
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False


def create_session(username: str) -> str:
    token = secrets.token_hex(32)
    _SESSIONS[token] = username
    return token


def get_session_user(token: str) -> str | None:
    return _SESSIONS.get(token)


def destroy_session(token: str):
    _SESSIONS.pop(token, None)
