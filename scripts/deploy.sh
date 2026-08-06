#!/usr/bin/env bash
set -euo pipefail

EXPECTED_ACCOUNT="913498135252"
AWS_REGION="${AWS_REGION:-ap-southeast-2}"
STACK_NAME="${STACK_NAME:-gosblo-production}"
CFN_EXECUTION_ROLE_ARN="${CFN_EXECUTION_ROLE_ARN:-arn:aws:iam::913498135252:role/gosblo/GosbloCloudFormationExecutionRole}"

if [[ "${AWS_REGION}" != "ap-southeast-2" ]]; then
  echo "Refusing to deploy outside ap-southeast-2 (Sydney)." >&2
  exit 1
fi

if [[ -z "${CONTACT_TO_EMAIL:-}" || -z "${CONTACT_FROM_EMAIL:-}" ]]; then
  echo "Set CONTACT_TO_EMAIL and CONTACT_FROM_EMAIL before deploying." >&2
  exit 1
fi

command -v aws >/dev/null || { echo "AWS CLI v2 is required." >&2; exit 1; }
command -v zip >/dev/null || { echo "zip is required." >&2; exit 1; }

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [[ "${ACCOUNT_ID}" != "${EXPECTED_ACCOUNT}" ]]; then
  echo "Refusing to deploy to AWS account ${ACCOUNT_ID}; expected ${EXPECTED_ACCOUNT}." >&2
  exit 1
fi

if [[ -n "${DOMAIN_NAME:-}" && -z "${CERTIFICATE_ARN:-}" ]]; then
  echo "CERTIFICATE_ARN is required when DOMAIN_NAME is set." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_BUCKET="gosblo-deployment-${ACCOUNT_ID}-${AWS_REGION}"
ARTIFACT_KEY="contact/$(shasum -a 256 "${ROOT_DIR}/infra/contact/handler.py" | awk '{print $1}').zip"
PACKAGE_DIR="$(mktemp -d)"
trap 'rm -rf "${PACKAGE_DIR}"' EXIT

if ! aws s3api head-bucket --bucket "${ARTIFACT_BUCKET}" 2>/dev/null; then
  aws s3api create-bucket \
    --bucket "${ARTIFACT_BUCKET}" \
    --region "${AWS_REGION}" \
    --create-bucket-configuration "LocationConstraint=${AWS_REGION}" >/dev/null
  aws s3api put-public-access-block \
    --bucket "${ARTIFACT_BUCKET}" \
    --public-access-block-configuration 'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
  aws s3api put-bucket-encryption \
    --bucket "${ARTIFACT_BUCKET}" \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
fi

(cd "${ROOT_DIR}/infra/contact" && zip -q "${PACKAGE_DIR}/contact.zip" handler.py)
aws s3 cp "${PACKAGE_DIR}/contact.zip" "s3://${ARTIFACT_BUCKET}/${ARTIFACT_KEY}" --only-show-errors

PARAMETERS=(
  "LambdaCodeBucket=${ARTIFACT_BUCKET}"
  "LambdaCodeKey=${ARTIFACT_KEY}"
  "ContactToEmail=${CONTACT_TO_EMAIL}"
  "ContactFromEmail=${CONTACT_FROM_EMAIL}"
  "DomainName=${DOMAIN_NAME:-}"
  "AlternateDomainName=${ALTERNATE_DOMAIN_NAME:-}"
  "CertificateArn=${CERTIFICATE_ARN:-}"
  "HostedZoneId=${HOSTED_ZONE_ID:-}"
)

aws cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/site.yaml" \
  --role-arn "${CFN_EXECUTION_ROLE_ARN}" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides "${PARAMETERS[@]}"

SITE_BUCKET="$(aws cloudformation describe-stacks --region "${AWS_REGION}" --stack-name "${STACK_NAME}" --query 'Stacks[0].Outputs[?OutputKey==`SiteBucketName`].OutputValue' --output text)"
DISTRIBUTION_ID="$(aws cloudformation describe-stacks --region "${AWS_REGION}" --stack-name "${STACK_NAME}" --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text)"
WEBSITE_URL="$(aws cloudformation describe-stacks --region "${AWS_REGION}" --stack-name "${STACK_NAME}" --query 'Stacks[0].Outputs[?OutputKey==`WebsiteUrl`].OutputValue' --output text)"

aws s3 sync "${ROOT_DIR}/site/" "s3://${SITE_BUCKET}/" --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths '/*' >/dev/null

echo "Deployment complete: ${WEBSITE_URL}"
