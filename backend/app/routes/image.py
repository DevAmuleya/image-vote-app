# Deprecated — superseded by GET /api/posts/{code} in app/routes/post.py



@router.get("/{image_id}")
async def get_image_details(image_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get details of an image including votes and comments.
    """
    result = await session.execute(
        select(Image)
        .where(Image.id == image_id)
        .options(selectinload(Image.comments))
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "success": True,
        "id": image.id,
        "url": image.image_url,
        "votes_count": image.votes_count,
        "comments_count": len(image.comments),
        "comments": [
            {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat()
            }
            for comment in image.comments
        ],
        "created_at": image.created_at.isoformat()
    }


@router.get("/{image_id}/comments")
async def get_image_comments(image_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get all comments for an image.
    """
    result = await session.execute(
        select(Image)
        .where(Image.id == image_id)
        .options(selectinload(Image.comments))
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "success": True,
        "image_id": image_id,
        "comments_count": len(image.comments),
        "comments": [
            {
                "id": comment.id,
                "content": comment.content,
                "created_at": comment.created_at.isoformat()
            }
            for comment in image.comments
        ]
    }
