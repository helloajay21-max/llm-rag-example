#!/bin/bash
set -euo pipefail

# Usage:
# ./create_azure_resources.sh <subscriptionId> <resourceGroup> <location> <planName> <webappName> <dockerhubUsername>
# Example:
# ./create_azure_resources.sh SUBSCRIPTION_ID mcprg eastus mcp-plan mcp-webapp mydockeruser

SUBSCRIPTION_ID=${1:-}
RESOURCE_GROUP=${2:-mcp-rg}
LOCATION=${3:-eastus}
PLAN_NAME=${4:-mcp-app-plan}
WEBAPP_NAME=${5:-mcp-webapp}
DOCKERHUB_USERNAME=${6:-}
IMAGE_NAME=mcp-streamlit

if [ -z "$SUBSCRIPTION_ID" ]; then
  echo "Subscription ID required as first argument"
  exit 1
fi
if [ -z "$DOCKERHUB_USERNAME" ]; then
  echo "Docker Hub username required as sixth argument"
  exit 1
fi

az account set --subscription "$SUBSCRIPTION_ID"
az group create -n "$RESOURCE_GROUP" -l "$LOCATION"

# Create App Service plan (Linux)
az appservice plan create -g "$RESOURCE_GROUP" -n "$PLAN_NAME" --is-linux --sku B1

# Create Web App for Containers
az webapp create -g "$RESOURCE_GROUP" -p "$PLAN_NAME" -n "$WEBAPP_NAME" --deployment-container-image-name "${DOCKERHUB_USERNAME}/${IMAGE_NAME}:latest"
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$WEBAPP_NAME" --settings WEBSITES_PORT=8501 SQLITE_DB_PATH=/home/data.db

echo "Resources created. Next steps: set GitHub secrets (AZURE_CREDENTIALS, KEY_VAULT_NAME, RESOURCE_GROUP, WEBAPP_NAME, DOCKERHUB_USERNAME, DOCKERHUB_TOKEN) and push to main/master."
