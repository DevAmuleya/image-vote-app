import os
import boto3
from botocore.config import Config as BotocoreConfig
from dotenv import load_dotenv

load_dotenv()

# Only attempt SSM when actually running inside AWS Lambda.
# Locally, boto3 would time out waiting for credentials/endpoint, blocking startup.
_IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ


def get_ssm_parameter(name: str, with_decryption=True):
    ssm = boto3.client(
        "ssm",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=BotocoreConfig(connect_timeout=3, retries={"max_attempts": 1})
    )
    response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
    return response["Parameter"]["Value"]


class Settings:
    if _IS_LAMBDA:
        try:
            DATABASE_URL   = get_ssm_parameter("/myapp/database_url")
            AWS_ACCESS_KEY = get_ssm_parameter("/myapp/aws_access_key")
            AWS_SECRET_KEY = get_ssm_parameter("/myapp/aws_secret_key")
            AWS_BUCKET     = get_ssm_parameter("/myapp/aws_bucket")
            AWS_REGION     = get_ssm_parameter("/myapp/aws_region")
            FB_APP_ID      = get_ssm_parameter("/myapp/fb_app_id")
            FB_APP_SECRET  = get_ssm_parameter("/myapp/fb_app_secret")
            FRONTEND_URL   = get_ssm_parameter("/myapp/frontend_url")
            JWT_SECRET     = get_ssm_parameter("/myapp/jwt_secret")
        except Exception as e:
            print(f"[WARN] Could not load SSM parameters, falling back to env vars: {e}")
            DATABASE_URL   = os.getenv("DATABASE_URL")
            AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
            AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
            AWS_BUCKET     = os.getenv("AWS_BUCKET")
            AWS_REGION     = os.getenv("AWS_REGION")
            FB_APP_ID      = os.getenv("FB_APP_ID")
            FB_APP_SECRET  = os.getenv("FB_APP_SECRET")
            FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://localhost:5173")
            JWT_SECRET     = os.getenv("JWT_SECRET", "change-me-in-production")
    else:
        # Local development — read directly from .env (no SSM)
        DATABASE_URL   = os.getenv("DATABASE_URL")
        AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
        AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
        AWS_BUCKET     = os.getenv("AWS_BUCKET")
        AWS_REGION     = os.getenv("AWS_REGION")
        FB_APP_ID      = os.getenv("FB_APP_ID")
        FB_APP_SECRET  = os.getenv("FB_APP_SECRET")
        FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://localhost:5173")
        JWT_SECRET     = os.getenv("JWT_SECRET", "change-me-in-production")


Config = Settings()
