"""
Facebook Graph API helper functions.

Photo upload to personal timelines requires the `publish_actions` permission,
which Facebook deprecated for new apps in 2018. These functions attempt the
Graph API calls and degrade gracefully (returning None) when the permission
is not available. The app functions correctly in all cases — photos are always
reliably available via their S3 URLs.

For Facebook Pages (not personal timelines), use pages_manage_posts permission
and substitute `/{page_id}/photos` and `/{page_id}/feed` below.
"""

import httpx
from typing import Optional


async def stage_photo_on_facebook(
    user_id: str,
    access_token: str,
    photo_url: str,
) -> Optional[str]:
    """
    Upload a photo to Facebook as an unpublished (staged) media object.
    Returns the Facebook media ID on success, None on failure.

    Requires: publish_actions (personal) or pages_manage_posts (Page).
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"https://graph.facebook.com/v21.0/{user_id}/photos",
                data={
                    "url": photo_url,
                    "published": "false",
                    "access_token": access_token,
                }
            )

        if res.status_code == 200:
            return res.json().get("id")

        return None  # Permission not available — photo stays on S3
    except Exception:
        return None


async def publish_facebook_post(
    user_id: str,
    access_token: str,
    media_ids: list[str],
    message: str = "Vote on my photos!"
) -> Optional[str]:
    """
    Create a Facebook feed post with the given staged media objects.
    Returns the Facebook post ID on success, None on failure.

    Requires: publish_actions (personal) or pages_manage_posts (Page).
    """
    if not media_ids:
        return None

    try:
        attached_media = [{"media_fbid": mid} for mid in media_ids]

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"https://graph.facebook.com/v21.0/{user_id}/feed",
                json={
                    "message": message,
                    "attached_media": attached_media,
                    "access_token": access_token,
                }
            )

        if res.status_code == 200:
            return res.json().get("id")

        return None
    except Exception:
        return None
