#!/bin/bash
set -euo pipefail

# Usage: ./grant_kv_access.sh <keyVaultName> <appId>
# Example: ./grant_kv_access.sh my-kv 00000000-0000-0000-0000-000000000000
# The script grants 'get' permission on secrets to the service principal (by appId).

KV_NAME=${1:-}
APP_ID=${2:-}

if [ -z "$KV_NAME" ] || [ -z "$APP_ID" ]; then
  echo "Usage: $0 <keyVaultName> <appId>"
  exit 1
fi

az keyvault set-policy --name "$KV_NAME" --spn "$APP_ID" --secret-permissions get

echo "Granted 'get' permission on secrets in $KV_NAME to appId $APP_ID"
