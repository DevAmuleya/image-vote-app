# Deprecated — vote logic lives in app/routes/post.py::cast_vote



async def cast_vote(db: AsyncSession, image_id: str, voter_fingerprint: str):
    """
    Cast a vote for an image.
    Returns the updated vote count.
    Raises exception if duplicate vote detected or image not found.
    
    Args:
        db: Database session
        image_id: ID of the image to vote on
        voter_fingerprint: Unique identifier for the voter (usually IP address)
    
    Returns:
        dict with message, image_id, and updated votes_count
    
    Raises:
        ValueError: If image not found
        IntegrityError: If duplicate vote (already voted)
    """
    try:
        # Verify image exists first
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            raise ValueError(f"Image with id {image_id} not found")

        # Try to create vote
        vote = Vote(
            image_id=image_id,
            voter_fingerprint=voter_fingerprint
        )

        db.add(vote)
        await db.flush()

        # Increment vote count on the image
        image.votes_count += 1
        db.add(image)

        await db.commit()
        await db.refresh(image)

        return {
            "message": "Vote recorded successfully",
            "image_id": image_id,
            "votes_count": image.votes_count
        }

    except IntegrityError as e:
        await db.rollback()
        raise ValueError("You have already voted on this post. You are not eligible to vote again.")
    except ValueError:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Failed to record vote: {str(e)}")