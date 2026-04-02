from fastapi import FastAPI
from app.routes import auth, post
from .middleware import register_middleware

app = FastAPI(
    title="Image Vote App API",
    description="In-Facebook photo voting platform — auth via Facebook OAuth, media on S3, data in Neon.",
    version="2.0.0"
)

register_middleware(app)

app.include_router(auth.router, prefix="/api/auth",  tags=["Auth"])
app.include_router(post.router, prefix="/api/posts", tags=["Posts"])


@app.get("/")
def root():
    return {
        "message": "Image Vote API v2 🚀",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth":        "POST /api/auth/facebook — exchange FB token, return user profile",
            "me":          "GET  /api/auth/me — return current user (Bearer token required)",
            "create_post": "POST /api/posts — upload 3-5 images, create post (auth required)",
            "get_post":    "GET  /api/posts/{code} — view post by shareable code (public)",
            "cast_vote":   "POST /api/posts/{post_id}/vote — vote on a photo (auth required)",
            "results":     "GET  /api/posts/{post_id}/results — view full vote results (public)"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "image-vote-api", "version": "2.0.0"}
