variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Short name prefix for all resources"
  type        = string
  default     = "image-vote"
}
