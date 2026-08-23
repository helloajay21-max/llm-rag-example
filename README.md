# MCP Project — Streamlit UI on Azure

A Streamlit app deployed to Azure App Service via Docker Hub and GitHub Actions.

Live app: https://mcp-ajay-streamlit-001.azurewebsites.net

---

## Local Development

### Prerequisites
- Python 3.11+
- OpenAI API key

### Run locally

```bash
cd mcp-project
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
streamlit run app.py
```

App runs at http://localhost:8501

### AI assistant capabilities

The app includes a professional AI assistant with:
- mode switch: General Assistant / Data Analyst / SQL Expert / Report Writer
- response style control: Concise / Balanced / Detailed
- optional CSV numeric summary context
- optional saved SQL-result context
- structured markdown output sections (Answer, Key Points, Evidence, Assumptions, Source Notes)

Optional environment variable:
- `OPENAI_MODEL` (default: `gpt-4o-mini`)

### Run with Docker locally

```bash
cd mcp-project
docker build -t mcp-streamlit .
docker run -p 8501:8501 -e OPENAI_API_KEY=sk-... mcp-streamlit
```

---

## Azure Deployment (GitHub Actions)

### One-time setup

#### 1. Prerequisites
- Azure CLI installed and logged in: `az login`
- Docker Hub account
- GitHub repo with this code

#### 2. Create Azure resources

```bash
# Create resource group
az group create --name Ajay-Practice --location centralindia

# Create App Service plan (Linux)
az appservice plan create --name mcp-app-plan --resource-group Ajay-Practice --sku B1 --is-linux

# Create Web App (container)
az webapp create --name mcp-ajay-streamlit-001 --resource-group Ajay-Practice --plan mcp-app-plan --deployment-container-image-name nginx
```

#### 3. Create service principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name mcp-github-sp \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/Ajay-Practice \
  --sdk-auth
```

Copy the full JSON output — this is your `AZURE_CREDENTIALS`.

#### 4. Add GitHub repository secrets

Go to: GitHub repo → Settings → Secrets and variables → Actions

| Secret name | Value |
|---|---|
| `AZURE_CREDENTIALS` | Full JSON from step 3 |
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Your Docker Hub access token |
| `RESOURCE_GROUP` | `Ajay-Practice` |
| `WEBAPP_NAME` | `mcp-ajay-streamlit-001` |
| `OPENAI_API_KEY` | Your OpenAI API key (starts with `sk-`) |

#### 5. Deploy

Push to `main` branch. The workflow `.github/workflows/azure-container-deploy.yml` will automatically:
1. Log in to Azure
2. Log in to Docker Hub
3. Build Docker image from `./mcp-project`
4. Push image to Docker Hub
5. Set container image on Azure Web App
6. Set app settings (`OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o-mini`, `WEBSITES_PORT=8501`, `SQLITE_DB_PATH=/home/data.db`)
7. Restart the Web App

---

## Update / Redeploy

Any push to `main` triggers automatic redeployment. No manual steps needed.

To force redeploy without a code change:
```bash
git commit --allow-empty -m "trigger deploy"
git push
```

---

## Running on a Corporate / Restricted System

If your corporate network blocks outbound ports or Docker Hub access:

**Option 1 — Run locally without Docker:**
```bash
pip install -r mcp-project/requirements.txt
cd mcp-project
streamlit run app.py
```
Access at http://localhost:8501

**Option 2 — Use the live Azure URL:**
- Simply open https://mcp-ajay-streamlit-001.azurewebsites.net in any browser
- No installation needed — the app is already hosted on Azure

**Option 3 — Corporate Azure subscription:**
- Ask your IT/Azure admin for a resource group
- Repeat the deployment steps using your corporate subscription ID
- The workflow file and Dockerfile work with any Azure subscription

---

## Azure Resources Used

| Resource | Name |
|---|---|
| Resource Group | `Ajay-Practice` |
| App Service Plan | `mcp-app-plan` |
| Web App | `mcp-ajay-streamlit-001` |
| Region | `Central India` |

---

## Security Notes

- Never commit `.env` or `az-creds.json`
- GitHub secrets are encrypted — safe for API keys
- Rotate your OpenAI key if it was ever accidentally committed
