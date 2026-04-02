"""
AWS Lambda entry point.
Mangum wraps the FastAPI ASGI app so Lambda can invoke it via API Gateway HTTP API.
"""
from mangum import Mangum
from app import app

handler = Mangum(app, lifespan="off")
