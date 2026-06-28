#!/bin/bash
# Runs inside LocalStack on startup — creates all required AWS resources.
# No set -e: individual creates are idempotent (already-exists errors are fine).

REGION="us-east-1"

echo "=== LocalStack init: waiting for DynamoDB service ==="
for i in $(seq 1 30); do
  awslocal dynamodb list-tables --region $REGION > /dev/null 2>&1 && break
  sleep 2
done

echo "=== LocalStack init: creating DynamoDB tables ==="

awslocal dynamodb create-table \
  --table-name osb-instances \
  --attribute-definitions AttributeName=instance_id,AttributeType=S \
  --key-schema AttributeName=instance_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION > /dev/null 2>&1 || true

awslocal dynamodb create-table \
  --table-name osb-bindings \
  --attribute-definitions AttributeName=binding_id,AttributeType=S \
  --key-schema AttributeName=binding_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION > /dev/null 2>&1 || true

awslocal dynamodb create-table \
  --table-name sovereign-services \
  --attribute-definitions AttributeName=service_id,AttributeType=S \
  --key-schema AttributeName=service_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION > /dev/null 2>&1 || true

echo "=== LocalStack init: creating SQS queue ==="

awslocal sqs create-queue \
  --queue-name osb-provisioning \
  --region $REGION > /dev/null 2>&1 || true

echo "=== LocalStack init: creating S3 bucket for Sovereign overrides ==="

awslocal s3 mb s3://sovereign-config --region $REGION > /dev/null 2>&1 || true

awslocal s3 cp - s3://sovereign-config/global.json <<'EOF'
{
  "default_timeout_ms": 30000,
  "default_retry_attempts": 3,
  "access_log_enabled": true
}
EOF

echo "=== LocalStack init: complete ==="
