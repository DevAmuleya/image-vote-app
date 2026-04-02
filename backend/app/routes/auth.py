from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
from app.db.main import get_session
from app.auth.service import verify_facebook_token_and_get_user
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter()


class FacebookTokenRequest(BaseModel):
    access_token: str


@router.post("/facebook")
async def facebook_login(
    payload: FacebookTokenRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Exchange a Facebook user access token for an application session JWT.
    Calls the Graph API exactly once to verify identity, upserts the user,
    then returns a signed JWT the client uses for all subsequent requests.
    The Facebook access_token is never needed again after this call.
    """
    user, session_token = await verify_facebook_token_and_get_user(payload.access_token, db)
    return {
        "success": True,
        "session_token": session_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "picture_url": user.picture_url,
            "created_at": user.created_at.isoformat()
        }
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "picture_url": current_user.picture_url,
            "created_at": current_user.created_at.isoformat()
        }
    }
