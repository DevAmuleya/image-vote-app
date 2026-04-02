# Deprecated — comments are part of Vote records in app/routes/post.py



@router.post("/")
async def create_comment(data: CommentCreate, db: AsyncSession = Depends(get_session)):
    """
    Add a comment to an image.
    
    Args:
        data: CommentCreate with image_id and content
        db: Database session
    
    Returns:
        Comment confirmation with ID and timestamp
    
    Raises:
        HTTPException: 400 for invalid data, 404 if image not found, 500 for server errors
    """
    try:
        if not data.image_id:
            raise HTTPException(status_code=400, detail="image_id is required")
        
        if not data.content or not data.content.strip():
            raise HTTPException(status_code=400, detail="Comment content is required")
        
        if len(data.content) > 1000:
            raise HTTPException(status_code=400, detail="Comment must be less than 1000 characters")
        
        result = await add_comment(db, data.image_id, data.content.strip())
        return {"success": True, **result}
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")