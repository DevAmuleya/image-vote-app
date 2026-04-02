#!/usr/bin/env bash
# deploy.sh — Full production deploy: backend (Lambda) + frontend (S3 + CloudFront).
#
# Usage:
#   bash scripts/deploy.sh
#
# Requirements:
#   - AWS CLI configured
#   - Docker Desktop running
#   - Terraform installed (https://developer.hashicorp.com/terraform/install)
#   - Node.js installed
#   - Run `bash scripts/setup-ssm.sh` at least once before first deploy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
INFRA_DIR="$ROOT/infrastructure"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
REGION="${AWS_REGION:-us-east-1}"

echo "========================================"
echo "  Image Vote — Production Deploy"
echo "========================================"

# ── Phase 1: Terraform (provision/update infrastructure) ──────────────────────
echo ""
echo "► Phase 1/4: Terraform apply..."
cd "$INFRA_DIR"
terraform init -upgrade -input=false
terraform apply -auto-approve -input=false

ECR_URL=$(terraform output -raw ecr_repository_url)
CF_URL=$(terraform output -raw cloudfront_url)
CF_ID=$(terraform output -raw cloudfront_distribution_id)
BUCKET=$(terraform output -raw frontend_bucket)
PHOTOS_BUCKET=$(terraform output -raw photos_bucket)

echo "  ECR:         $ECR_URL"
echo "  CloudFront:  $CF_URL"
echo "  Frontend S3: $BUCKET"
echo "  Photos S3:   $PHOTOS_BUCKET"

# ── Phase 2: Build & push Docker image to ECR ─────────────────────────────────
echo ""
echo "► Phase 2/4: Build & push backend Docker image..."
cd "$BACKEND_DIR"

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

docker build --platform linux/amd64 -t "${ECR_URL}:latest" .
docker push "${ECR_URL}:latest"

# Update Lambda to use the new image
FUNCTION_NAME=$(cd "$INFRA_DIR" && terraform output -raw cloudfront_url | sed 's|https://||' | head -c 1 && echo "" || true)
# Derive function name from Terraform state
FUNCTION_NAME="image-vote-api"
echo "  Updating Lambda function: $FUNCTION_NAME"
aws lambda update-function-code \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --image-uri "${ECR_URL}:latest" \
  --no-cli-pager \
  --output text > /dev/null

# Wait for Lambda update to complete
aws lambda wait function-updated \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME"
echo "  Lambda updated."

# ── Phase 3: Push FRONTEND_URL and PHOTOS_BUCKET to SSM ──────────────────────
echo ""
echo "► Phase 3/4: Updating SSM params..."
aws ssm put-parameter \
  --region "$REGION" \
  --name "/myapp/frontend_url" \
  --value "$CF_URL" \
  --type SecureString \
  --overwrite \
  --no-cli-pager \
  --output text > /dev/null
echo "  ✓ /myapp/frontend_url → $CF_URL"

aws ssm put-parameter \
  --region "$REGION" \
  --name "/myapp/aws_bucket" \
  --value "$PHOTOS_BUCKET" \
  --type SecureString \
  --overwrite \
  --no-cli-pager \
  --output text > /dev/null
echo "  ✓ /myapp/aws_bucket → $PHOTOS_BUCKET"

# Keep backend/.env in sync so local dev always uses the Terraform-managed bucket
if grep -q "^AWS_BUCKET=" "$BACKEND_DIR/.env"; then
  sed -i "s|^AWS_BUCKET=.*|AWS_BUCKET=$PHOTOS_BUCKET|" "$BACKEND_DIR/.env"
else
  echo "AWS_BUCKET=$PHOTOS_BUCKET" >> "$BACKEND_DIR/.env"
fi
echo "  ✓ backend/.env AWS_BUCKET → $PHOTOS_BUCKET"
echo "  Done."

# ── Phase 4: Build & deploy frontend ──────────────────────────────────────────
echo ""
echo "► Phase 4/4: Build & deploy frontend..."
cd "$FRONTEND_DIR"

# Write production env
cat > .env.production <<EOF
VITE_FB_APP_ID=$(grep VITE_FB_APP_ID .env | cut -d= -f2)
VITE_API_URL=$CF_URL
EOF

npm ci
npm run build

echo "  Syncing to s3://$BUCKET ..."
aws s3 sync dist/ "s3://$BUCKET" \
  --region "$REGION" \
  --delete \
  --cache-control "max-age=31536000,immutable" \
  --exclude "index.html"

# index.html must not be cached (always fresh)
aws s3 cp dist/index.html "s3://$BUCKET/index.html" \
  --region "$REGION" \
  --cache-control "no-cache,no-store,must-revalidate"

echo "  Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$CF_ID" \
  --paths "/*" \
  --no-cli-pager \
  --output text > /dev/null

echo ""
echo "========================================"
echo "  Deploy complete!"
echo "  App URL: $CF_URL"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Open your Facebook App → Settings → Basic"
echo "     Set App Domains & Site URL to: $CF_URL"
echo "  2. Facebook Login → Settings → Valid OAuth Redirect URIs:"
echo "     Add: $CF_URL"
echo "  3. Switch your Facebook App to Live mode"
echo ""
