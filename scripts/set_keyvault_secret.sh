#!/bin/bash
set -euo pipefail

# Usage: ./set_keyvault_secret.sh <keyVaultName> <openai_key>
# Example: ./set_keyvault_secret.sh my-kv "sk-..."

KV_NAME=${1:-}
OPENAI_KEY=${2:-}

if [ -z "$KV_NAME" ] || [ -z "$OPENAI_KEY" ]; then
  echo "Usage: $0 <keyVaultName> <openai_key>"
  exit 1
fi

az keyvault secret set --vault-name "$KV_NAME" -n OpenAIKey --value "$OPENAI_KEY"

echo "Secret 'OpenAIKey' set in Key Vault: $KV_NAME"
