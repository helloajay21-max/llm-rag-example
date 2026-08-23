Azure deployment guide (Docker Hub + Azure App Service)

1) Fill `.env`

Copy `.env.example` to `.env` and set these values:

- `OPENAI_API_KEY`: used locally.
- `OPENAI_KEY_FOR_KEYVAULT`: same OpenAI key, used once to write Key Vault secret `OpenAIKey`.
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION`
- `RESOURCE_GROUP`, `APP_SERVICE_PLAN`, `WEBAPP_NAME`, `KEY_VAULT_NAME`
- `IMAGE_NAME` (default `mcp-streamlit`)

2) Create Azure resources

```bash
./scripts/create_azure_resources.sh <AZURE_SUBSCRIPTION_ID> <RESOURCE_GROUP> <AZURE_LOCATION> <APP_SERVICE_PLAN> <WEBAPP_NAME> <DOCKERHUB_USERNAME>
```

3) Create service principal for GitHub Actions

```bash
az ad sp create-for-rbac \
  --name mcp-github-sp \
  --role Contributor \
  --scopes /subscriptions/<AZURE_SUBSCRIPTION_ID> \
  --sdk-auth > az-creds.json
```

4) Put OpenAI key in Key Vault and grant access

```bash
./scripts/set_keyvault_secret.sh <KEY_VAULT_NAME> "<OPENAI_KEY_FOR_KEYVAULT>"
APP_ID=$(jq -r .clientId az-creds.json)
./scripts/grant_kv_access.sh <KEY_VAULT_NAME> "$APP_ID"
```

5) Add GitHub repository secrets

Required secrets:
- `AZURE_CREDENTIALS` (content of `az-creds.json`)
- `KEY_VAULT_NAME`
- `RESOURCE_GROUP`
- `WEBAPP_NAME`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Optional helper:

```bash
./scripts/add_github_secrets.sh <owner/repo> ./az-creds.json <KEY_VAULT_NAME> <RESOURCE_GROUP> <WEBAPP_NAME>
```

Then add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` in GitHub secrets UI (or with `gh secret set`).

6) Deploy

Push to `main` or `master`. Workflow `.github/workflows/azure-container-deploy.yml` will:
- build and push image to Docker Hub
- set container image on the Web App
- set app settings: `OPENAI_API_KEY`, `WEBSITES_PORT=8501`, `SQLITE_DB_PATH=/home/data.db`
- restart the Web App

Security notes:
- Never commit `.env` or `az-creds.json`.
- Delete `az-creds.json` after secrets are added.
