import time
import jwt
from app.config import Config

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def create_session_token(user_id: str) -> str:
    """Issue a signed JWT containing the user's ID. Valid for 30 days."""
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + _TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=_ALGORITHM)


def decode_session_token(token: str) -> str:
    """Verify and decode a session JWT. Returns the user_id (sub claim).
    Raises jwt.PyJWTError if invalid or expired."""
    payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[_ALGORITHM])
    return payload["sub"]

