output "ecr_repository_url" {
  description = "Push Docker images here"
  value       = aws_ecr_repository.app.repository_url
}

output "api_gateway_url" {
  description = "Direct API Gateway URL (use CloudFront /api/* in production)"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cloudfront_url" {
  description = "Your production app URL — use this everywhere"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "Needed to invalidate the CDN cache after a frontend deploy"
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_bucket" {
  description = "S3 bucket name for the React build"
  value       = aws_s3_bucket.frontend.bucket
}

output "photos_bucket" {
  description = "S3 bucket name for photo uploads"
  value       = aws_s3_bucket.photos.bucket
}
