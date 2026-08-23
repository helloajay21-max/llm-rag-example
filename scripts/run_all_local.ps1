<#
PowerShell equivalent of run_all_local.sh for Windows/Azure Cloud Shell (PowerShell).
Usage:
  .\run_all_local.ps1 -SubscriptionId <SUB_ID> -KeyVaultName <KV_NAME> -OpenAIKey "<sk-...>" -GitHubRepo <owner/repo> -ResourceGroup <rg> -WebAppName <webapp> -DockerHubUsername <user> -DockerHubToken <token> [-SpName <sp-name>]

Notes:
- Requires az CLI installed and authenticated.
- Requires gh CLI to automatically set GitHub secrets (optional).
- Creates az-creds.json locally; delete it after uploading to GitHub secrets.
#>
param(
  [Parameter(Mandatory=$true)] [string]$SubscriptionId,
  [Parameter(Mandatory=$true)] [string]$KeyVaultName,
  [Parameter(Mandatory=$true)] [string]$OpenAIKey,
  [Parameter(Mandatory=$true)] [string]$GitHubRepo,
  [Parameter(Mandatory=$true)] [string]$ResourceGroup,
  [Parameter(Mandatory=$true)] [string]$WebAppName,
  [Parameter(Mandatory=$false)] [string]$DockerHubUsername = "",
  [Parameter(Mandatory=$false)] [string]$DockerHubToken = "",
  [Parameter(Mandatory=$false)] [string]$SpName = "mcp-github-sp"
)

function Fail($msg){ Write-Error $msg; exit 1 }

# Check az exists
if (-not (Get-Command az -ErrorAction SilentlyContinue)) { Fail "az CLI not found. Install Azure CLI and login before running this script." }

Write-Host "1) Creating service principal '$SpName'..."
$spJson = az ad sp create-for-rbac --name $SpName --role Contributor --scopes "/subscriptions/$SubscriptionId" --sdk-auth 2>&1
if ($LASTEXITCODE -ne 0) { Fail "Failed to create service principal: $spJson" }
$spJson | Out-File -FilePath az-creds.json -Encoding utf8

# Parse clientId from JSON
try {
  $creds = Get-Content -Raw az-creds.json | ConvertFrom-Json
  $appId = $creds.clientId
} catch {
  Fail "Unable to parse az-creds.json: $_"
}

Write-Host "2) Storing OpenAI key in Key Vault '$KeyVaultName'..."
$setOut = az keyvault secret set --vault-name $KeyVaultName -n OpenAIKey --value $OpenAIKey 2>&1
if ($LASTEXITCODE -ne 0) { Fail "Failed to set Key Vault secret: $setOut" }

Write-Host "3) Granting Key Vault 'get' permission to SP appId: $appId"
$grantOut = az keyvault set-policy --name $KeyVaultName --spn $appId --secret-permissions get 2>&1
if ($LASTEXITCODE -ne 0) { Fail "Failed to set Key Vault policy: $grantOut" }

# Optionally add GitHub secrets via gh
if (Get-Command gh -ErrorAction SilentlyContinue) {
  Write-Host "4) Adding secrets to GitHub repo $GitHubRepo using gh CLI..."
  try {
    gh secret set AZURE_CREDENTIALS --repo $GitHubRepo --body-file az-creds.json | Out-Null
    gh secret set KEY_VAULT_NAME --repo $GitHubRepo --body $KeyVaultName | Out-Null
    gh secret set RESOURCE_GROUP --repo $GitHubRepo --body $ResourceGroup | Out-Null
    gh secret set WEBAPP_NAME --repo $GitHubRepo --body $WebAppName | Out-Null
    if ($DockerHubUsername -ne "" -and $DockerHubToken -ne "") {
      gh secret set DOCKERHUB_USERNAME --repo $GitHubRepo --body $DockerHubUsername | Out-Null
      gh secret set DOCKERHUB_TOKEN --repo $GitHubRepo --body $DockerHubToken | Out-Null
    }
    Write-Host "GitHub secrets set."
  } catch {
    Write-Warning "Failed to set some GitHub secrets via gh: $_\nYou can add them manually in the GitHub repository settings.";
  }
} else {
  Write-Warning "gh CLI not found. Skipping GitHub secrets upload. Add AZURE_CREDENTIALS, KEY_VAULT_NAME, RESOURCE_GROUP and WEBAPP_NAME via GitHub UI or install gh." 
}

Write-Host "Done. az-creds.json created locally. Delete it after verifying secrets were uploaded: Remove-Item az-creds.json"
Write-Host "Next: push your repo to GitHub to trigger CI/CD, or build/push Docker image locally and configure the Web App."
