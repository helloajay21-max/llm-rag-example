#!/bin/bash
set -euo pipefail

# Usage: ./add_github_secrets.sh <repo> <az_credentials_file> <key_vault_name> <resource_group> <webapp_name>
# Requires GitHub CLI (gh) authenticated and permissions to set repo secrets.
# Example:
# ./add_github_secrets.sh myorg/myrepo ./az-creds.json my-kv my-rg my-webapp

REPO=${1:-}
AZ_CREDS_FILE=${2:-}
KV_NAME=${3:-}
RESOURCE_GROUP=${4:-}
WEBAPP_NAME=${5:-}

if [ -z "$REPO" ] || [ -z "$AZ_CREDS_FILE" ] || [ -z "$KV_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$WEBAPP_NAME" ]; then
  echo "Usage: $0 <repo> <az_credentials_file> <key_vault_name> <resource_group> <webapp_name>"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install from https://cli.github.com/"
  exit 1
fi

# AZURE_CREDENTIALS
gh secret set AZURE_CREDENTIALS --repo "$REPO" --body-file "$AZ_CREDS_FILE"

# Key Vault name and resource settings
gh secret set KEY_VAULT_NAME --repo "$REPO" --body "$KV_NAME"
gh secret set RESOURCE_GROUP --repo "$REPO" --body "$RESOURCE_GROUP"
gh secret set WEBAPP_NAME --repo "$REPO" --body "$WEBAPP_NAME"

echo "Set AZURE_CREDENTIALS, KEY_VAULT_NAME, RESOURCE_GROUP and WEBAPP_NAME for $REPO"

echo "Note: Set DOCKERHUB_USERNAME and DOCKERHUB_TOKEN separately (they may be sensitive)."
