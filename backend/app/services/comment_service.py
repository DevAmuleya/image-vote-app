# Deprecated — comments are stored as Vote.comment in app/db/models.py



async def add_comment(db: AsyncSession, image_id: str, content: str):
    """
    Add a comment to an image.
    
    Args:
        db: Database session
        image_id: ID of the image to comment on
        content: Comment text
    
    Returns:
        dict with comment ID, image_id, content, and timestamp
    
    Raises:
        ValueError: If image not found or content is invalid
    """
    try:
        # Validate input
        if not content or not content.strip():
            raise ValueError("Comment content cannot be empty")
        
        if len(content) > 1000:
            raise ValueError("Comment must be less than 1000 characters")
        
        # Verify image exists
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            raise ValueError(f"Image with id {image_id} not found")

        comment = Comment(
            id=str(uuid4()),
            image_id=image_id,
            content=content.strip()
        )

        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        return {
            "id": comment.id,
            "image_id": comment.image_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat()
        }

    except ValueError:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Failed to add comment: {str(e)}")