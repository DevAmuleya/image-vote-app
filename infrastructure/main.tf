terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # ── Remote state backend ────────────────────────────────────────────────────
  # Required so CI/CD (GitHub Actions) shares state across pipeline runs.
  #
  # One-time bootstrap (run locally, before first CI run):
  #   aws s3 mb s3://YOUR-TFSTATE-BUCKET --region us-east-1
  #   (The bucket is created automatically by the CI workflow on first run too —
  #    see the "Create Terraform state bucket" step in deploy.yml)
  #
  # Then set the GitHub secret TF_STATE_BUCKET to YOUR-TFSTATE-BUCKET.
  # The workflow calls: terraform init -backend-config="bucket=$TF_STATE_BUCKET"
  # If you prefer local state (single machine only), remove this block entirely.
  backend "s3" {
    # Bucket and region are supplied at init time via -backend-config flags
    # so no sensitive values are hardcoded here.
    key          = "image-vote/terraform.tfstate"
    use_lockfile = true # native S3 locking (replaces deprecated dynamodb_table)
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ─── ECR repository (stores Docker images) ───────────────────────────────────

resource "aws_ecr_repository" "app" {
  name                 = "${var.app_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ─── IAM role for Lambda ──────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ssm_s3" {
  name = "${var.app_name}-lambda-ssm-s3"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/myapp/*"
      },
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.photos.arn,
          "${aws_s3_bucket.photos.arn}/*"
        ]
      }
    ]
  })
}

# ─── Lambda function (container image) ───────────────────────────────────────

resource "aws_lambda_function" "app" {
  function_name = "${var.app_name}-api"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      CORS_ORIGINS = "https://${aws_cloudfront_distribution.frontend.domain_name}"
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_basic]
}

# ─── API Gateway HTTP API ─────────────────────────────────────────────────────

resource "aws_apigatewayv2_api" "app" {
  name          = "${var.app_name}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.app.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.app.execution_arn}/*/*"
}

# ─── S3 bucket for photo uploads ─────────────────────────────────────────────

resource "aws_s3_bucket" "photos" {
  bucket = "${var.app_name}-photos-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "photos" {
  bucket                  = aws_s3_bucket.photos.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = [
      "https://${aws_cloudfront_distribution.frontend.domain_name}",
      "http://localhost:5173"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# ─── S3 bucket for frontend (private, served via CloudFront) ─────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.app_name}-frontend-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── CloudFront Origin Access Control ────────────────────────────────────────

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.app_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
        }
      }
    }]
  })

  depends_on = [aws_cloudfront_distribution.frontend]
}

# ─── CloudFront distribution ──────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  # S3 origin (React app)
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  # API Gateway origin (FastAPI backend)
  # invoke_url is "https://{id}.execute-api.{region}.amazonaws.com/" — strip
  # both the scheme and the trailing slash to get a bare domain name.
  origin {
    domain_name = trimsuffix(replace(aws_apigatewayv2_stage.default.invoke_url, "https://", ""), "/")
    origin_id   = "apigw-backend"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # /api/* → API Gateway
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "apigw-backend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Origin"]
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # /* → S3 (React app, handle SPA routing)
  default_cache_behavior {
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # Return index.html for all unknown paths (React Router SPA)
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
