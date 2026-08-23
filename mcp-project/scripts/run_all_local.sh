#!/bin/bash
set -euo pipefail

# Run all local setup steps for MCP project.
# Usage:
# ./run_all_local.sh <SUBSCRIPTION_ID> <KEY_VAULT_NAME> <OPENAI_KEY> <GITHUB_REPO> <RESOURCE_GROUP> <WEBAPP_NAME> <DOCKERHUB_USERNAME> <DOCKERHUB_TOKEN> [SP_NAME]
# Example:
# ./run_all_local.sh SUB_ID ajayvault21 "sk-..." myorg/myrepo myrg mywebapp mydockeruser mydockertoken mcp-github-sp

SUBSCRIPTION_ID=${1:-}
KV_NAME=${2:-}
OPENAI_KEY=${3:-}
GITHUB_REPO=${4:-}
RESOURCE_GROUP=${5:-}
WEBAPP_NAME=${6:-}
DOCKERHUB_USERNAME=${7:-}
DOCKERHUB_TOKEN=${8:-}
SP_NAME=${9:-mcp-github-sp}

if [ -z "$SUBSCRIPTION_ID" ] || [ -z "$KV_NAME" ] || [ -z "$OPENAI_KEY" ] || [ -z "$GITHUB_REPO" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$WEBAPP_NAME" ]; then
  echo "Usage: $0 <SUBSCRIPTION_ID> <KEY_VAULT_NAME> <OPENAI_KEY> <GITHUB_REPO> <RESOURCE_GROUP> <WEBAPP_NAME> <DOCKERHUB_USERNAME> <DOCKERHUB_TOKEN> [SP_NAME]"
  exit 1
fi

echo "1) Creating service principal: $SP_NAME"
az ad sp create-for-rbac --name "$SP_NAME" --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID --sdk-auth > az-creds.json

echo "2) Storing OpenAI key in Key Vault $KV_NAME"
az keyvault secret set --vault-name "$KV_NAME" -n OpenAIKey --value "$OPENAI_KEY"

# extract appId
if command -v jq >/dev/null 2>&1; then
  APP_ID=$(jq -r .clientId az-creds.json)
else
  APP_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv)
fi

echo "3) Granting Key Vault access to SP appId: $APP_ID"
az keyvault set-policy --name "$KV_NAME" --spn "$APP_ID" --secret-permissions get

# Add GitHub secrets using gh CLI
if command -v gh >/dev/null 2>&1; then
  echo "4) Adding secrets to GitHub repo: $GITHUB_REPO"
  gh secret set AZURE_CREDENTIALS --repo "$GITHUB_REPO" --body-file az-creds.json || echo "Failed to set AZURE_CREDENTIALS"
  gh secret set KEY_VAULT_NAME --repo "$GITHUB_REPO" --body "$KV_NAME"
  gh secret set RESOURCE_GROUP --repo "$GITHUB_REPO" --body "$RESOURCE_GROUP"
  gh secret set WEBAPP_NAME --repo "$GITHUB_REPO" --body "$WEBAPP_NAME"
  if [ -n "$DOCKERHUB_USERNAME" ] && [ -n "$DOCKERHUB_TOKEN" ]; then
    gh secret set DOCKERHUB_USERNAME --repo "$GITHUB_REPO" --body "$DOCKERHUB_USERNAME"
    gh secret set DOCKERHUB_TOKEN --repo "$GITHUB_REPO" --body "$DOCKERHUB_TOKEN"
  fi
  echo "GitHub secrets set (where possible)."
else
  echo "gh CLI not found — skipping GitHub secrets. Install gh and run the commands in README_AZURE.md or use the GitHub UI."
fi

echo "Cleanup: remove local az-creds.json (recommended)"
# rm -f az-creds.json   # commented by default; uncomment to auto-delete

echo "Completed local setup steps. Next: configure workflow secrets in GitHub and push to trigger CI, or build/push Docker image locally."

echo "Notes: Docker build/push steps are not included because Cloud Shell typically doesn't support Docker. Use your local machine to build and push the image, or rely on GitHub Actions to build." 
