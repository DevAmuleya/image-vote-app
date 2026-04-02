# Deprecated — image persistence is handled inside app/routes/post.py::create_post



async def save_images(db: AsyncSession, file_urls: list[str]):
    """
    Save uploaded image URLs to the database.
    
    Args:
        db: Database session
        file_urls: List of S3 file URLs (3-5 URLs)
    
    Returns:
        List of created image objects with their IDs and metadata
    
    Raises:
        ValueError: If file_urls count is not between 3-5 or if DB operation fails
    """
    if not file_urls:
        raise ValueError("No file URLs provided")
    
    if len(file_urls) < 3 or len(file_urls) > 5:
        raise ValueError(f"Must save between 3-5 images, got {len(file_urls)}")
    
    # Validate URLs are not empty
    for url in file_urls:
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL in file_urls list")

    created_images = []

    try:
        for url in file_urls:
            image = Image(
                id=str(uuid4()),
                image_url=url.strip(),
                votes_count=0
            )
            db.add(image)
            created_images.append(image)

        await db.commit()

        # Refresh all images to get timestamp info
        for img in created_images:
            await db.refresh(img)

        return [
            {
                "id": img.id,
                "image_url": img.image_url,
                "votes_count": img.votes_count,
                "created_at": img.created_at.isoformat()
            }
            for img in created_images
        ]

    except ValueError:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise ValueError(f"Failed to save images to database: {str(e)}")
