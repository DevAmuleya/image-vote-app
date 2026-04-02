import os
import boto3
from app.config import Config

_IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

if _IS_LAMBDA:
    # In Lambda the execution role grants S3 access — no explicit credentials needed
    s3 = boto3.client("s3", region_name=Config.AWS_REGION)
else:
    # Local development — use credentials from .env
    s3 = boto3.client(
        "s3",
        aws_access_key_id=Config.AWS_ACCESS_KEY,
        aws_secret_access_key=Config.AWS_SECRET_KEY,
        region_name=Config.AWS_REGION,
    )
