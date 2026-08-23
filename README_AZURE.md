Azure deployment guide (GitHub → Azure App Service via GitHub Actions CI/CD)

This project is set up for automated deployment from GitHub to Azure App Service using GitHub Actions. The workflow in `.github/workflows/azure-container-deploy.yml` builds a Docker image, pushes it to Docker Hub, and updates the Azure Web App automatically whenever code is pushed to `main`.

1) Fill `.env`

Copy `.env.example` to `.env` and set these values:

- `OPENAI_API_KEY`: used for OpenAI calls in local and deployed app runtime.
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION`
- `RESOURCE_GROUP`, `APP_SERVICE_PLAN`, `WEBAPP_NAME`
- `IMAGE_NAME` (default `mcp-streamlit`)
- `SQLITE_DB_PATH` (local default is `data.db`)

2) Create Azure resources

```bash
./scripts/create_azure_resources.sh <AZURE_SUBSCRIPTION_ID> <RESOURCE_GROUP> <AZURE_LOCATION> <APP_SERVICE_PLAN> <WEBAPP_NAME> <DOCKERHUB_USERNAME>
```

3) Create a service principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name mcp-github-sp \
  --role Contributor \
  --scopes /subscriptions/<AZURE_SUBSCRIPTION_ID> \
  --sdk-auth > az-creds.json
```

4) Add GitHub repository secrets

Required secrets:

- `AZURE_CREDENTIALS` = content of `az-creds.json`
- `RESOURCE_GROUP`
- `WEBAPP_NAME`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `OPENAI_API_KEY`

Optional helper for secrets creation:

```bash
./scripts/add_github_secrets.sh <owner/repo> ./az-creds.json <RESOURCE_GROUP> <WEBAPP_NAME>
```

5) Deploy automatically with GitHub → Azure CI/CD

Push changes to the `main` branch. The GitHub Actions workflow will:

- check out the repository from GitHub
- authenticate to Azure using `AZURE_CREDENTIALS`
- log in to Docker Hub
- build the Docker image
- push it to Docker Hub
- update the Azure App Service container image
- set app settings including `OPENAI_API_KEY`, `WEBSITES_PORT=8501`, and `SQLITE_DB_PATH=/home/data.db`
- restart the Azure Web App

6) Local verification

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Security notes:

- Never commit real `.env` or Azure credentials files.
- Remove `az-creds.json` after the GitHub secrets are configured.
- Keep `OPENAI_API_KEY` in GitHub repository secrets and Azure app settings, not in source control.
