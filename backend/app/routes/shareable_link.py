# Deprecated — shareable codes are on the Post model, served by GET /api/posts/{code}



# Request schema for creating shareable link
class CreateShareableLinkRequest(BaseModel):
    image_ids: list[str]


@router.post("/create")
async def create_shareable_link(payload: CreateShareableLinkRequest, session: AsyncSession = Depends(get_session)):
    """
    Create a shareable link for a collection of images.
    
    Args:
        payload: {"image_ids": ["id1", "id2", ...]} (3-5 image IDs)
        session: Database session
    
    Returns:
        Shareable link details with unique code
    
    Raises:
        HTTPException: 400 for validation errors, 404 if images not found, 500 for server errors
    """
    try:
        image_ids = payload.image_ids
        
        if not image_ids:
            raise HTTPException(status_code=400, detail="image_ids list cannot be empty")

        if len(image_ids) < 3 or len(image_ids) > 5:
            raise HTTPException(status_code=400, detail=f"Must provide 3-5 image IDs, got {len(image_ids)}")

        # Verify all images exist and are unique
        verified_ids = set()
        for image_id in image_ids:
            result = await session.exec(select(Image).where(Image.id == image_id))
            image = result.scalar_one_or_none()
            if not image:
                raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
            verified_ids.add(image_id)

        if len(verified_ids) != len(image_ids):
            raise HTTPException(status_code=400, detail="Duplicate image IDs provided")

        # Create unique shareable link
        unique_link = secrets.token_urlsafe(16)

        shareable_link = ShareableLink(
            id=str(uuid4()),
            link=unique_link
        )

        session.add(shareable_link)
        await session.flush()

        # Associate images with the link
        for image_id in verified_ids:
            result = await session.exec(select(Image).where(Image.id == image_id))
            image = result.scalar_one()
            image.shareable_link_id = shareable_link.id
            session.add(image)

        await session.commit()

        return {
            "success": True,
            "link_id": shareable_link.id,
            "shareable_url": f"/api/shareable-links/view/{unique_link}",
            "unique_code": unique_link,
            "images_count": len(verified_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create shareable link: {str(e)}")


@router.get("/view/{link}")
async def view_images(link: str, session: AsyncSession = Depends(get_session)):
    """
    Retrieve all images for a shareable link with their vote counts and comments.
    
    Args:
        link: Unique shareable link code
        session: Database session
    
    Returns:
        Images with vote counts and comment counts
    
    Raises:
        HTTPException: 404 if link not found, 500 for server errors
    """
    try:
        result = await session.exec(
            select(ShareableLink).where(ShareableLink.link == link)
        )
        shareable = result.scalar_one_or_none()

        if not shareable:
            raise HTTPException(status_code=404, detail="Shareable link not found")

        # Eagerly load comments using selectinload to avoid lazy-loading issues in async context
        result = await session.exec(
            select(Image)
            .where(Image.shareable_link_id == shareable.id)
            .options(selectinload(Image.comments))
        )
        images = result.scalars().all()

        return {
            "success": True,
            "link_id": shareable.id,
            "created_at": shareable.created_at.isoformat(),
            "images_count": len(images),
            "images": [
                {
                    "id": img.id,
                    "url": img.image_url,
                    "votes_count": img.votes_count,
                    "comments_count": len(img.comments),
                    "created_at": img.created_at.isoformat()
                }
                for img in images
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve images: {str(e)}")