Azure deployment guide (Docker Hub + Azure App Service)

1) Configure local `.env` (for local run)

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- Azure resource values (`AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `WEBAPP_NAME`, etc.)

2) Required GitHub repository secrets

In GitHub repo -> Settings -> Secrets and variables -> Actions, add:

- `AZURE_CREDENTIALS` (JSON from `az ad sp create-for-rbac --sdk-auth`)
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `RESOURCE_GROUP`
- `WEBAPP_NAME`
- `OPENAI_API_KEY`

3) Deployment workflow

On push to `main`/`master`, `.github/workflows/azure-container-deploy.yml` will:

- log in to Azure
- log in to Docker Hub
- build and push image from `./mcp-project`
- configure Azure Web App to use the new image
- set app settings (`OPENAI_API_KEY`, `WEBSITES_PORT=8501`, `SQLITE_DB_PATH=/home/data.db`)
- restart the Web App

4) Assistant configuration in app

The app supports these assistant modes:

- General Assistant
- Data Analyst
- SQL Expert
- Report Writer

It also supports:

- response style selection (Concise/Balanced/Detailed)
- optional CSV summary context
- optional saved SQL summary context
- structured response format with source-notes section

5) Security notes

- Never commit `.env` or credential JSON files.
- Keep keys only in GitHub Secrets or Azure App Settings.
- Rotate OpenAI keys immediately if exposed.
