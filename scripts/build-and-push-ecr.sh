#!/usr/bin/env bash
set -euo pipefail

: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}" 
: "${AWS_REGION:?Set AWS_REGION}" 
: "${IMAGE_NAME:=cybergrader}" 
: "${IMAGE_TAG:=latest}" 

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}"

aws ecr describe-repositories --repository-names "${IMAGE_NAME}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${IMAGE_NAME}" >/dev/null

echo "Logging into Amazon ECR ${AWS_REGION}"
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Building image ${ECR_URI}:${IMAGE_TAG}"
docker build -t "${ECR_URI}:${IMAGE_TAG}" .

echo "Pushing image"
docker push "${ECR_URI}:${IMAGE_TAG}"

echo "Image pushed to ${ECR_URI}:${IMAGE_TAG}"
