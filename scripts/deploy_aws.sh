#!/bin/bash
set -e

# Default settings
REGION=${AWS_REGION:-us-east-1}
REPO_NAME="restaurant-waitlist-app"
STACK_NAME="restaurant-waitlist-stack"

echo "======================================================"
echo " AWS CloudFormation Deployment Orchestrator"
echo "======================================================"

# 1. Verify AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "Error: aws-cli is not installed or not in PATH."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS CLI is not configured with valid credentials."
    echo "Please run 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Verified AWS credentials. Deploying to Account: ${ACCOUNT_ID} in Region: ${REGION}"

# 2. Ensure ECR Repo exists
echo "Checking for ECR repository '${REPO_NAME}'..."
if ! aws ecr describe-repositories --repository-names "${REPO_NAME}" --region "${REGION}" >/dev/null 2>&1; then
    echo "Repository not found. Creating ECR repository..."
    aws ecr create-repository --repository-name "${REPO_NAME}" --region "${REGION}"
fi

# 3. Build and Push Docker image
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"
IMAGE_TAG=$(date +%Y%m%d%H%M%S)
FULL_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"

echo "Building Docker image: ${FULL_IMAGE_URI}..."
# Ensure we are in the project root
cd "$(dirname "$0")/.."
docker build -t "${FULL_IMAGE_URI}" -f Dockerfile .

echo "Logging into AWS ECR..."
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "Pushing Docker image to ECR..."
docker push "${FULL_IMAGE_URI}"

# 4. Deploy CloudFormation Stack
echo "Deploying CloudFormation stack: ${STACK_NAME}..."
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name "${STACK_NAME}" \
  --parameter-overrides ImageUri="${FULL_IMAGE_URI}" \
  --capabilities CAPABILITY_IAM \
  --region "${REGION}"

# 5. Output Results
echo "Deployment successful! Retrieving the Application URL..."
APP_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`AppURL`].OutputValue' \
  --output text)

echo "Validating deployment health..."
# The EC2 instance needs a few minutes to boot up, install docker, and launch the stack
MAX_ATTEMPTS=30
ATTEMPT=1
HEALTHY=false
echo "Polling application health at ${APP_URL}/api/tables..."

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -s -f -m 5 "${APP_URL}/api/tables" > /dev/null; then
        echo "Health check passed! Application is online, healthy, and connected to the database."
        HEALTHY=true
        break
    fi
    echo "Attempt ${ATTEMPT}/${MAX_ATTEMPTS}: Application is not online yet. Retrying in 10s..."
    sleep 10
    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$HEALTHY" = false ]; then
    echo "Error: Application failed the health check and did not become online within 5 minutes."
    exit 1
fi

echo "======================================================"
echo " Application is live and healthy at: ${APP_URL}"
echo "======================================================"
