#!/usr/bin/env bash
# Post-hackathon teardown: stop ALL Google Cloud costs for AgriNet.
#
#   PROJECT_ID=agrinet-fed-2026 ./deploy/teardown.sh
#
# Deleting the project removes every resource inside it (Cloud Run services,
# Artifact Registry images, Firestore data, secrets, build history) and ends
# all billing for it. The project stays recoverable for ~30 days via the
# Cloud console, then is purged.
#
# The code keeps working locally afterwards: SQLite storage, cached satellite
# snapshots, and DEMO_MODE need no cloud at all.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID (e.g. agrinet-fed-2026)}"

echo "This will DELETE project '$PROJECT_ID' and everything in it."
read -r -p "Type the project id to confirm: " CONFIRM
if [ "$CONFIRM" != "$PROJECT_ID" ]; then
  echo "Confirmation mismatch — aborting."
  exit 1
fi

gcloud projects delete "$PROJECT_ID" --quiet

echo ""
echo "Project deletion requested. Billing for it stops now."
echo "Also consider deleting/rotating the Gemini API key at"
echo "https://aistudio.google.com/apikey if it was created outside this project."
