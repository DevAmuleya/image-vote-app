from typing import Optional
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession
import jwt
from app.db.main import get_session
from app.auth.utils import decode_session_token
from app.db.models import User


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_session)
) -> User:
    """
    Require a valid session JWT in the Authorization header.
    Verifies the token locally (no Facebook API call) and returns the User.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header with Bearer session token required"
        )
    token = authorization.split(" ", 1)[1]
    try:
        user_id = decode_session_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_optional_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """
    Optional auth — returns the User if a valid session JWT is present, else None.
    Used on public endpoints that can optionally personalise the response.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        user_id = decode_session_token(token)
    except jwt.PyJWTError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
