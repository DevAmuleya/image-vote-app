import httpx
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from app.db.models import User
from app.auth.utils import create_session_token


async def verify_facebook_token_and_get_user(token: str, db: AsyncSession) -> tuple[User, str]:
    """
    Verify a Facebook user access token with the Graph API exactly once.
    Upserts the user in the DB and returns (User, session_jwt).
    The JWT is what the client stores and sends on all future requests —
    Facebook's token is never needed again after this call.
    Raises HTTP 401 if the token is invalid or the Graph API call fails.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            "https://graph.facebook.com/me",
            params={
                "fields": "id,name,email,picture.type(large)",
                "access_token": token
            }
        )

    if res.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Facebook access token")

    data = res.json()

    if "error" in data:
        raise HTTPException(
            status_code=401,
            detail=data["error"].get("message", "Invalid Facebook access token")
        )

    fb_user_id: str = data["id"]
    picture_url: Optional[str] = (
        data.get("picture", {}).get("data", {}).get("url")
    )

    result = await db.execute(select(User).where(User.id == fb_user_id))
    user = result.scalar_one_or_none()

    if user:
        user.name = data["name"]
        if data.get("email"):
            user.email = data["email"]
        if picture_url:
            user.picture_url = picture_url
    else:
        user = User(
            id=fb_user_id,
            name=data["name"],
            email=data.get("email"),
            picture_url=picture_url
        )
        db.add(user)

    user.last_seen_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    session_token = create_session_token(user.id)
    return user, session_token
