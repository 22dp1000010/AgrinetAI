#!/usr/bin/env bash
# Deploy AgriNet to Cloud Run: two state nodes + frontend.
# Prereqs: gcloud CLI authenticated, a project with Cloud Run + Cloud Build enabled.
#
#   export PROJECT_ID=your-project REGION=asia-south1 GEMINI_API_KEY=xxx
#   ./deploy/deploy.sh
#
# Run from the repo root. Idempotent — rerun to redeploy after changes.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-asia-south1}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
DEMO_MODE="${DEMO_MODE:-1}"

gcloud config set project "$PROJECT_ID"

echo "=== Deploying state nodes (skeleton pass to obtain URLs) ==="
for NODE in ts od; do
  STATE_ID=$(echo "$NODE" | tr '[:lower:]' '[:upper:]')
  gcloud run deploy "agrinet-node-$NODE" \
    --source ./backend \
    --region "$REGION" \
    --allow-unauthenticated \
    --min-instances 0 --memory 512Mi \
    --set-env-vars "STATE_ID=$STATE_ID,DEMO_MODE=$DEMO_MODE,GEMINI_API_KEY=$GEMINI_API_KEY"
done

TS_URL=$(gcloud run services describe agrinet-node-ts --region "$REGION" --format 'value(status.url)')
OD_URL=$(gcloud run services describe agrinet-node-od --region "$REGION" --format 'value(status.url)')
echo "TS node: $TS_URL"
echo "OD node: $OD_URL"

echo "=== Wiring peers (federation over the public internet) ==="
gcloud run services update agrinet-node-ts --region "$REGION" \
  --update-env-vars "PEERS=$OD_URL"
gcloud run services update agrinet-node-od --region "$REGION" \
  --update-env-vars "PEERS=$TS_URL"

echo "=== Deploying frontend (node URLs baked at build time) ==="
gcloud run deploy agrinet-frontend \
  --source ./frontend \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 0 --memory 256Mi \
  --build-env-vars-file <(printf 'VITE_NODE_TS: "%s"\nVITE_NODE_OD: "%s"\n' "$TS_URL" "$OD_URL")

FRONTEND_URL=$(gcloud run services describe agrinet-frontend --region "$REGION" --format 'value(status.url)')

echo ""
echo "=== AgriNet is live ==="
echo "Frontend:       $FRONTEND_URL"
echo "Telangana node: $TS_URL"
echo "Odisha node:    $OD_URL"
echo ""
echo "Seed the demo:  python backend/scripts/seed_demo_data.py --node $TS_URL --peer $OD_URL"
echo "Warm before recording: curl \$URL/v1/health on all three services."
