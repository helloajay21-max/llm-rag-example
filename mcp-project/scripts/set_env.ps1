<#
PowerShell helper to set local user environment variables for development.
Usage (example):
  .\set_env.ps1 -DockerUser "myuser" -DockerToken "mytoken" -ResourceGroup "rg" -WebApp "mcp-webapp" -KeyVaultName "kv-name" -SubscriptionId "<sub-id>" -OpenAIKey "<sk-...>"

Note: It's safer to store secrets in GitHub repository secrets for CI. This script sets Windows user environment variables using setx.
#>
param(
  [string]$DockerUser = "",
  [string]$DockerToken = "",
  [string]$ResourceGroup = "",
  [string]$WebApp = "",
  [string]$KeyVaultName = "",
  [string]$SubscriptionId = "",
  [string]$OpenAIKey = "",
  [string]$SqliteDbPath = "data.db"
)

if ($DockerUser -ne "") {
  setx DOCKERHUB_USERNAME $DockerUser
  Write-Host "Set DOCKERHUB_USERNAME"
}
if ($DockerToken -ne "") {
  setx DOCKERHUB_TOKEN $DockerToken
  Write-Host "Set DOCKERHUB_TOKEN"
}
if ($ResourceGroup -ne "") {
  setx RESOURCE_GROUP $ResourceGroup
  Write-Host "Set RESOURCE_GROUP"
}
if ($WebApp -ne "") {
  setx WEBAPP_NAME $WebApp
  Write-Host "Set WEBAPP_NAME"
}
if ($KeyVaultName -ne "") {
  setx KEY_VAULT_NAME $KeyVaultName
  Write-Host "Set KEY_VAULT_NAME"
}
if ($SubscriptionId -ne "") {
  setx AZURE_SUBSCRIPTION_ID $SubscriptionId
  Write-Host "Set AZURE_SUBSCRIPTION_ID"
}
if ($OpenAIKey -ne "") {
  setx OPENAI_API_KEY $OpenAIKey
  setx OPENAI_KEY_FOR_KEYVAULT $OpenAIKey
  Write-Host "Set OPENAI_API_KEY and OPENAI_KEY_FOR_KEYVAULT"
}
if ($SqliteDbPath -ne "") {
  setx SQLITE_DB_PATH $SqliteDbPath
  Write-Host "Set SQLITE_DB_PATH"
}

setx IMAGE_NAME mcp-streamlit | Out-Null
setx WEBSITES_PORT 8501 | Out-Null
Write-Host "Set IMAGE_NAME and WEBSITES_PORT"

Write-Host "Reminder: Add AZURE_CREDENTIALS, KEY_VAULT_NAME, RESOURCE_GROUP, WEBAPP_NAME, DOCKERHUB_USERNAME and DOCKERHUB_TOKEN as GitHub repository secrets for CI/CD."
