<#
PowerShell helper to install WSL2 & Docker Desktop (via winget), build the Docker image, run locally, and optionally push to Docker Hub.

Usage (run as Administrator):
  .\install_and_run_docker.ps1 -OpenAIKey '<sk-...>' -DockerHubUsername '<user>' -DockerHubToken '<token>' -Tag '<tag>'

Parameters:
  -OpenAIKey        Optional. Will be passed to container as OPENAI_KEY when run locally.
  -DockerHubUsername Optional. If provided together with DockerHubToken, script will login and push image.
  -DockerHubToken    Optional. Docker Hub access token or password.
  -Tag               Optional. Image tag to use for push (default: latest)

Notes:
- This script uses winget to install Docker Desktop. On some systems winget may not be available.
- Requires an elevated PowerShell session (Run as Administrator) for feature installs.
- After Docker Desktop install, user may need to sign into Docker Desktop GUI.
- The script waits for Docker to become available before building.
- Do NOT commit secrets. Use environment variables or GitHub secrets for CI.
#>
param(
  [string]$OpenAIKey = "",
  [string]$DockerHubUsername = "",
  [string]$DockerHubToken = "",
  [string]$Tag = "latest"
)

function Ensure-Admin {
  $current = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($current)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Open PowerShell 'Run as administrator' and re-run."
    exit 1
  }
}

function Run-Command {
  param($cmd)
  Write-Host "> $cmd"
  iex $cmd
}

Ensure-Admin

# 1) Ensure WSL is installed
Write-Host "Checking WSL..."
try {
  wsl --status > $null 2>&1
  Write-Host "WSL appears installed."
} catch {
  Write-Host "Installing WSL (this may take a moment)."
  Run-Command "wsl --install"
  Write-Host "WSL installation started. You may need to restart your machine."
}

# 2) Install Docker Desktop via winget
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Warning "winget not available. Please install Docker Desktop manually from https://www.docker.com/get-started"
} else {
  Write-Host "Installing Docker Desktop via winget..."
  Run-Command "winget install --id Docker.DockerDesktop -e --source winget"
  Write-Host "Docker Desktop install command issued. If installer requires UI interaction, please complete it." 
}

# 3) Start Docker Desktop if installed
$dockerExePaths = @("C:\Program Files\Docker\Docker\Docker Desktop.exe", "C:\Program Files\Docker\Docker\DockerDesktop.exe")
$dockerStarted = $false
foreach ($path in $dockerExePaths) {
  if (Test-Path $path) {
    Write-Host "Starting Docker Desktop from: $path"
    Start-Process -FilePath $path -WindowStyle Hidden
    $dockerStarted = $true
    break
  }
}
if (-not $dockerStarted) { Write-Host "Docker Desktop not found in Program Files. If installed, start Docker Desktop manually." }

# 4) Wait for docker CLI to be available
Write-Host "Waiting for Docker daemon to become available (timeout 180s)..."
$start = Get-Date
while ((Get-Date) - $start).TotalSeconds -lt 180 {
  try {
    docker version --format '{{.Server.Version}}' > $null 2>&1
    Write-Host "Docker is available."
    break
  } catch {
    Start-Sleep -Seconds 3
  }
}
try { docker version --format '{{.Server.Version}}' > $null 2>&1 } catch { Write-Error "Docker did not start within timeout. Please open Docker Desktop and ensure it is running."; exit 1 }

# 5) Build the image
$imageName = "mcp-streamlit"
$localTag = "$imageName:local"
Write-Host "Building Docker image: $localTag"
Run-Command "docker build -t $localTag ."

# 6) Run container
$runEnv = ""
if ($OpenAIKey -ne "") {
  $runEnv = "-e OPENAI_KEY=$OpenAIKey"
}
Write-Host "Running container (accessible at http://localhost:8501)..."
Write-Host "Press Ctrl+C to stop the container"
try {
  Run-Command "docker run --rm -p 8501:8501 $runEnv $localTag"
} catch {
  Write-Error "Container exited or failed to start: $_"
}

# 7) Optional: tag & push to Docker Hub (if credentials provided)
if ($DockerHubUsername -and $DockerHubToken) {
  $remoteImage = "$DockerHubUsername/$imageName:$Tag"
  Write-Host "Tagging image as $remoteImage"
  Run-Command "docker tag $localTag $remoteImage"
  Write-Host "Logging in to Docker Hub (using provided token)"
  # Use docker login with stdin to avoid showing token in process list
  $login = "docker login --username $DockerHubUsername --password-stdin"
  $pw = $DockerHubToken
  $pw | docker login --username $DockerHubUsername --password-stdin
  if ($LASTEXITCODE -ne 0) { Write-Warning "Docker login may have failed. Check credentials and try again." } else {
    Write-Host "Pushing $remoteImage"
    Run-Command "docker push $remoteImage"
  }
} else {
  Write-Host "Docker Hub credentials not provided. Skipping push step."
}

Write-Host "Script finished. If you built and pushed the image, configure your Web App or CI to use the pushed image."