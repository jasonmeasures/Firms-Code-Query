#!/usr/bin/env bash
# Packages the API for Elastic Beanstalk once terraform outputs are exported.
set -euo pipefail
cd "$(dirname "$0")/backend"
if [[ -z "${EB_APP_NAME:-}" || -z "${EB_ENV_NAME:-}" || -z "${EB_S3_BUCKET:-}" ]]; then
  echo "Set EB_APP_NAME, EB_ENV_NAME, and EB_S3_BUCKET from terraform output."
  exit 1
fi
echo "Deploy hook is ready for ${EB_APP_NAME}/${EB_ENV_NAME}. Wire the zip upload when the CHB environment exists."
