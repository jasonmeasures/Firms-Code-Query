#!/usr/bin/env bash
# Builds the static UI. Amplify upload waits on the app id from terraform.
set -euo pipefail
cd "$(dirname "$0")/frontend"
npm run build
if [[ -z "${AMPLIFY_APP_ID:-}" ]]; then
  echo "Frontend built in frontend/dist. Set AMPLIFY_APP_ID to start an Amplify release."
  exit 0
fi
aws amplify start-job --app-id "$AMPLIFY_APP_ID" --branch-name main --job-type RELEASE
