# Deprecated — file upload is handled inside POST /api/posts in app/routes/post.py


# Request schema for save-images
class SaveImagesRequest(BaseModel):
    urls: list[str]


@router.post("/upload")
async def upload(payload: ImageUploadRequest, db: AsyncSession = Depends(get_session)):
    """
    Generate presigned URLs for image uploads.
    Client will use these URLs to upload directly to S3.
    
    Returns:
        - List of presigned upload URLs
        - File URLs for client-side reference
        - Keys for database storage
    """
    try:
        presigned_urls = await create_upload(payload.files)
        return presigned_urls
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-direct")
async def upload_direct(files: list[UploadFile] = File(...)):
    """
    Upload files directly through backend to S3.
    This avoids CORS issues by proxying through the backend.
    
    Args:
        files: List of files to upload (3-5 images)
    
    Returns:
        List of uploaded file URLs and keys with success status
    
    Raises:
        HTTPException: 400 if validation fails, 500 if upload fails
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        if len(files) < 3 or len(files) > 5:
            raise HTTPException(status_code=400, detail="Must upload exactly 3 to 5 images")
        
        # Validate file types
        allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        for file in files:
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file type: {file.filename}. Allowed: jpg, png, gif, webp"
                )
        
        uploaded_files = []
        failed_files = []
        
        for file in files:
            try:
                result = await upload_file_to_s3(file)
                if result:
                    uploaded_files.append(result)
                else:
                    failed_files.append(file.filename)
            except Exception as e:
                failed_files.append(f"{file.filename}: {str(e)}")
        
        if failed_files:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to upload: {', '.join(failed_files)}"
            )
        
        if len(uploaded_files) != len(files):
            raise HTTPException(
                status_code=500, 
                detail="Some files failed to upload. Please try again."
            )
        
        return {"success": True, "files": uploaded_files, "count": len(uploaded_files)}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/save-images")
async def save_uploaded_images(payload: SaveImagesRequest, db: AsyncSession = Depends(get_session)):
    """
    Save uploaded image URLs to database.
    Call this endpoint after client successfully uploads files to S3.
    
    Args:
        payload: {"urls": ["https://...", "https://...", ...]}
    
    Returns:
        Success status with list of saved images and their IDs
    
    Raises:
        HTTPException: 400 for validation errors, 500 for database errors
    """
    try:
        if not payload.urls:
            raise HTTPException(status_code=400, detail="No URLs provided")
        
        images = await save_images(db, payload.urls)
        return {"success": True, "images": images, "count": len(images)}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save images: {str(e)}")