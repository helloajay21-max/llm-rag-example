Local env setup

This folder contains helpers to set local environment variables for development only.

Do NOT commit real secrets to the repository. Instead, add these as GitHub repository secrets:
- AZURE_CREDENTIALS (output from `az ad sp create-for-rbac --sdk-auth`)
- KEY_VAULT_NAME
- DOCKERHUB_USERNAME
- DOCKERHUB_TOKEN
- RESOURCE_GROUP
- WEBAPP_NAME

To set local user env vars on Windows (PowerShell):
  .\set_env.ps1 -DockerUser "myuser" -DockerToken "mytoken" -ResourceGroup "rg" -WebApp "mcp-webapp" -KeyVaultName "kv" -SubscriptionId "<sub-id>" -OpenAIKey "<sk-...>"

After running setx, open a new terminal to access the variables.
