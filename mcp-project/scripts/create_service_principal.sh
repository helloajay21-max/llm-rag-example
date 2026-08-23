#!/bin/bash
set -euo pipefail

# Usage: ./create_service_principal.sh <subscriptionId> <sp-name>
# Example: ./create_service_principal.sh SUBSCRIPTION_ID mcp-github-sp

SUBSCRIPTION_ID=${1:-}
SP_NAME=${2:-mcp-github-sp}

if [ -z "$SUBSCRIPTION_ID" ]; then
  echo "Subscription ID required as first argument"
  echo "Usage: $0 <subscriptionId> <sp-name>"
  exit 1
fi

echo "Creating service principal '$SP_NAME' with Contributor role on subscription $SUBSCRIPTION_ID..."

az ad sp create-for-rbac --name "$SP_NAME" --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID --sdk-auth

cat <<'EOF'

Save the JSON output and add it to GitHub as the AZURE_CREDENTIALS secret.
If you have `gh` installed you can run:
  gh secret set AZURE_CREDENTIALS --body "$(az ad sp create-for-rbac --name \"$SP_NAME\" --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID --sdk-auth)"

EOF
