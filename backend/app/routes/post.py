from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
import asyncio
import secrets
import uuid
from html import escape

from app.db.main import get_session
from app.db.models import Post, Photo, Vote, User
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.services.upload_service import upload_file_to_s3, generate_presigned_url_from_key, generate_presigned_get_url
from app.config import Config

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CastVoteRequest(BaseModel):
    photo_id: str
    comment: Optional[str] = Field(default=None, max_length=1000)


# ─── Create Post ─────────────────────────────────────────────────────────────

@router.post("")
async def create_post(
    files: list[UploadFile] = File(...),
    caption: Optional[str] = Form(default=None, max_length=500),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload 3-5 images to create a new Post.

    Flow:
      1. Validate and upload each file to S3 (reliable, always succeeds).
      2. Attempt to stage each photo on Facebook via the Graph API and obtain
         a facebook_media_id (requires publish_actions / pages_manage_posts;
         degrades gracefully when unavailable).
      3. Attempt to create a Facebook feed post from the staged media IDs
         (same permission requirement; also degrades gracefully).
      4. Persist the Post and Photo records in Neon DB with both S3 URLs and
         any Facebook IDs obtained.
      5. Return a unique shareable_code for the link.
    """
    if not files or len(files) < 3 or len(files) > 5:
        raise HTTPException(status_code=400, detail="Must upload 3 to 5 images")

    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    for f in files:
        if f.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {f.filename}. Allowed: jpg, png, gif, webp"
            )


    # Step 1: Upload all files to S3 concurrently
    results = await asyncio.gather(*[upload_file_to_s3(f) for f in files])
    for f, result in zip(files, results):
        if not result:
            raise HTTPException(status_code=500, detail=f"Failed to upload {f.filename} to S3")
    uploaded = list(results)

    # Step 2 & 3: Facebook photo staging requires the publish_actions permission,
    # which Facebook no longer grants to new apps. Skip entirely to avoid 15-second
    # timeout attempts per photo. Photos are always served reliably from S3.
    fb_media_ids = [None] * len(uploaded)
    fb_post_id = None

    # Step 4: Persist in Neon DB
    shareable_code = secrets.token_urlsafe(16)

    post = Post(
        id=str(uuid.uuid4()),
        creator_id=current_user.id,
        shareable_code=shareable_code,
        facebook_post_id=fb_post_id,
        caption=caption
    )
    db.add(post)
    await db.flush()

    for idx, (item, fb_media_id) in enumerate(zip(uploaded, fb_media_ids)):
        photo = Photo(
            id=str(uuid.uuid4()),
            post_id=post.id,
            media_url=item["file_url"],
            s3_key=item["key"],      # stable unique marker for this photo
            facebook_media_id=fb_media_id,
            position=idx
        )
        db.add(photo)

    await db.commit()
    await db.refresh(post)

    return {
        "success": True,
        "post_id": post.id,
        "shareable_code": shareable_code,
        "caption": caption,
        "facebook_post_id": fb_post_id,
        "photos_count": len(uploaded)
    }


# ─── Get Post by Shareable Code ──────────────────────────────────────────────

@router.get("/{code}")
async def get_post(
    code: str,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Retrieve a post by its shareable code with photos and vote counts.
    Public endpoint. If the request includes a valid Authorization header,
    the response also includes the authenticated user's existing vote (if any).
    """
    result = await db.execute(
        select(Post)
        .where(Post.shareable_code == code)
        .options(
            selectinload(Post.creator),
            selectinload(Post.photos),
            selectinload(Post.votes).selectinload(Vote.voter)
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    photos_sorted = sorted(post.photos, key=lambda p: p.position)

    # Check current user's existing vote
    user_vote = None
    if current_user:
        for vote in post.votes:
            if vote.voter_id == current_user.id:
                user_vote = {
                    "photo_id": vote.photo_id,
                    "comment": vote.comment,
                    "voted_at": vote.voted_at.isoformat()
                }
                break

    return {
        "success": True,
        "post_id": post.id,
        "shareable_code": code,
        "caption": post.caption,
        "created_at": post.created_at.isoformat(),
        "creator": {
            "id": post.creator.id,
            "name": post.creator.name,
            "picture_url": post.creator.picture_url
        } if post.creator else None,
        # total_votes is the stored counter — no Python aggregation needed
        "total_votes": post.total_votes,
        "user_vote": user_vote,
        "photos": [
            {
                "id": photo.id,
                # Use s3_key for presigning if available (preferred), fall back to URL extraction
                "media_url": (
                    generate_presigned_url_from_key(photo.s3_key)
                    if photo.s3_key
                    else generate_presigned_get_url(photo.media_url)
                ),
                "s3_key": photo.s3_key,
                "facebook_media_id": photo.facebook_media_id,
                "position": photo.position,
                # vote_count is the stored counter — accurate without aggregation
                "vote_count": photo.vote_count
            }
            for photo in photos_sorted
        ],
        "votes": [
            {
                "voter": {
                    "id": vote.voter.id,
                    "name": vote.voter.name,
                    "picture_url": vote.voter.picture_url
                } if vote.voter else None,
                "photo_id": vote.photo_id,
                "comment": vote.comment,
                "voted_at": vote.voted_at.isoformat()
            }
            for vote in post.votes
        ]
    }


# ─── Cast Vote ───────────────────────────────────────────────────────────────

@router.post("/{post_id}/vote")
async def cast_vote(
    post_id: str,
    payload: CastVoteRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cast one vote for a photo within a post. Authentication required.

    Rules enforced:
    - Each user may vote only once per post (HTTP 409 if already voted).
    - The selected photo must belong to the post (HTTP 404 otherwise).
    - An optional comment (≤ 1000 chars) may accompany the vote.
    """
    # Verify post exists
    result = await db.execute(select(Post).where(Post.id == post_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post not found")

    # Verify photo belongs to this post
    result = await db.execute(
        select(Photo).where(Photo.id == payload.photo_id, Photo.post_id == post_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Photo not found in this post")

    # Enforce one-vote constraint before attempting DB insert
    result = await db.execute(
        select(Vote).where(Vote.post_id == post_id, Vote.voter_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already voted on this post")

    vote = Vote(
        post_id=post_id,
        photo_id=payload.photo_id,
        voter_id=current_user.id,
        comment=payload.comment.strip() if payload.comment else None
    )
    db.add(vote)

    # Atomically increment both counters in the same transaction as the vote insert.
    # Using SQL UPDATE (not ORM read-modify-write) to avoid race conditions.
    await db.execute(
        update(Photo)
        .where(Photo.id == payload.photo_id)
        .values(vote_count=Photo.vote_count + 1)
    )
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(total_votes=Post.total_votes + 1)
    )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="You have already voted on this post")

    return {
        "success": True,
        "message": "Vote recorded",
        "post_id": post_id,
        "photo_id": payload.photo_id,
        "comment": vote.comment
    }


# ─── Get Vote Results ────────────────────────────────────────────────────────

@router.get("/{post_id}/results")
async def get_results(post_id: str, db: AsyncSession = Depends(get_session)):
    """
    Get full vote results for a post, including per-photo counts and
    each voter's name, picture, selected photo, and comment.
    Public endpoint.
    """
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.photos),
            selectinload(Post.votes).selectinload(Vote.voter)
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    photo_vote_counts = {photo.id: 0 for photo in post.photos}
    for vote in post.votes:
        photo_vote_counts[vote.photo_id] = photo_vote_counts.get(vote.photo_id, 0) + 1

    return {
        "success": True,
        "post_id": post_id,
        "total_votes": len(post.votes),
        "photos": [
            {
                "id": photo.id,
                "media_url": generate_presigned_get_url(photo.media_url),
                "position": photo.position,
                "vote_count": photo_vote_counts[photo.id]
            }
            for photo in sorted(post.photos, key=lambda p: p.position)
        ],
        "votes": [
            {
                "voter": {
                    "id": vote.voter.id,
                    "name": vote.voter.name,
                    "picture_url": vote.voter.picture_url
                },
                "photo_id": vote.photo_id,
                "comment": vote.comment,
                "voted_at": vote.created_at.isoformat()
            }
            for vote in sorted(post.votes, key=lambda v: v.created_at)
        ]
    }


# ─── Open Graph Metadata ─────────────────────────────────────────────────────

@router.get("/{code}/og", response_class=HTMLResponse, include_in_schema=False)
async def get_post_og(
    code: str,
    db: AsyncSession = Depends(get_session)
):
    """
    Returns an HTML page with Open Graph meta tags for the post.
    Facebook's crawler reads this when the link is shared.
    Human visitors are immediately redirected to the React frontend via meta-refresh.
    """
    result = await db.execute(
        select(Post)
        .where(Post.shareable_code == code)
        .options(selectinload(Post.photos))
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    frontend_url = Config.FRONTEND_URL.rstrip("/")
    redirect_url = f"{frontend_url}/share/{code}"

    # Use the first photo (sorted by position) for the og:image.
    # Generate a long-lived presigned URL (7 days) so Facebook's cache stays valid.
    photos_sorted = sorted(post.photos, key=lambda p: p.position)
    og_image = ""
    if photos_sorted:
        first = photos_sorted[0]
        og_image = (
            generate_presigned_url_from_key(first.s3_key, expires_in=604800)
            if first.s3_key
            else generate_presigned_get_url(first.media_url)
        )

    title = escape(post.caption or "Vote for my photo!")
    description = escape(
        f"{post.caption} — Click to vote for the best image."
        if post.caption
        else "Click to vote for the best image."
    )
    safe_redirect = escape(redirect_url)
    safe_image = escape(og_image)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:image" content="{safe_image}" />
  <meta property="og:url" content="{safe_redirect}" />
  <meta property="og:type" content="website" />
  <meta http-equiv="refresh" content="0; url={safe_redirect}" />
</head>
<body>
  <p>Redirecting… <a href="{safe_redirect}">Click here to vote</a></p>
</body>
</html>"""

    return HTMLResponse(content=html)
