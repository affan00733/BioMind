#!/usr/bin/env bash
set -euo pipefail

# Usage: ./create_scheduler.sh <PROJECT_ID> <REGION> <SERVICE_URL> <SCHEDULE>
PROJECT=${1:-$GOOGLE_CLOUD_PROJECT}
REGION=${2:-us-central1}
URL=${3:-}
SCHEDULE=${4:-"*/15 * * * *"} # default every 15 minutes

if [ -z "$PROJECT" ] || [ -z "$URL" ]; then
  echo "Usage: $0 <PROJECT_ID> [REGION] <CLOUD_RUN_URL> [CRON_SCHEDULE]"; exit 1
fi

JOB_NAME=biomind-runner-trigger

gcloud scheduler jobs create http $JOB_NAME --schedule="$SCHEDULE" --http-method=POST --uri="$URL" --project="$PROJECT" --location="$REGION" --oidc-service-account-email="$PROJECT@appspot.gserviceaccount.com"

echo "Created scheduler job $JOB_NAME -> $URL ($SCHEDULE)"
