#!/usr/bin/env bash
# setup-ssm.sh — Push all secrets from backend/.env to AWS SSM Parameter Store.
# Run this ONCE before the first deploy, and again whenever you change a secret.
#
# Usage:
#   bash scripts/setup-ssm.sh
#
# Requirements: AWS CLI configured with a user that has ssm:PutParameter permission.

set -euo pipefail

ENV_FILE="$(dirname "$0")/../backend/.env"
REGION="${AWS_REGION:-us-east-1}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

echo "Pushing secrets to SSM (region: $REGION)..."

put_param() {
  local name="$1"
  local value="$2"
  aws ssm put-parameter \
    --region "$REGION" \
    --name "$name" \
    --value "$value" \
    --type SecureString \
    --overwrite \
    --no-cli-pager \
    --output text > /dev/null
  echo "  ✓ $name"
}

# Read .env and push each key
while IFS='=' read -r key value || [[ -n "$key" ]]; do
  # Skip comments and blank lines
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  # Strip surrounding quotes from value
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"

  case "$key" in
    DATABASE_URL)   put_param "/myapp/database_url"   "$value" ;;
    AWS_ACCESS_KEY) put_param "/myapp/aws_access_key" "$value" ;;
    AWS_SECRET_KEY) put_param "/myapp/aws_secret_key" "$value" ;;
    AWS_BUCKET)     put_param "/myapp/aws_bucket"     "$value" ;;
    AWS_REGION)     put_param "/myapp/aws_region"     "$value" ;;
    FB_APP_ID)      put_param "/myapp/fb_app_id"      "$value" ;;
    FB_APP_SECRET)  put_param "/myapp/fb_app_secret"  "$value" ;;
    JWT_SECRET)     put_param "/myapp/jwt_secret"     "$value" ;;
  esac
done < "$ENV_FILE"

echo ""
echo "All secrets pushed. Don't forget to also push FRONTEND_URL after deploy:"
echo "  aws ssm put-parameter --region $REGION --name /myapp/frontend_url --value https://YOUR_CLOUDFRONT_URL --type SecureString --overwrite"
