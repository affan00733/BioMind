#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run_deploy.sh <PROJECT_ID> <REGION> <SERVICE_NAME>
PROJECT=${1:-$GOOGLE_CLOUD_PROJECT}
REGION=${2:-us-central1}
SERVICE=${3:-biomind-runner}

if [ -z "$PROJECT" ]; then
  echo "Usage: $0 <PROJECT_ID> [REGION] [SERVICE_NAME]"; exit 1
fi

gcloud builds submit --project "$PROJECT" --tag gcr.io/$PROJECT/$SERVICE
gcloud run deploy $SERVICE --image gcr.io/$PROJECT/$SERVICE --region $REGION --platform managed --project $PROJECT --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT,LOCATION=us-central1
