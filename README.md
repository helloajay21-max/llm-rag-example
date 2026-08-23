MCP Project — Streamlit UI

This repository contains a minimal Streamlit app packaged for deployment to Azure App Service (Linux) using a Docker container. The GitHub Actions workflow builds the image, pushes it to Docker Hub, and updates the Web App to use the new image.

Quick start (local):

1. python -m pip install -r requirements.txt
2. python -m streamlit run app.py

Azure setup (high level):

1. Copy `.env.example` to `.env` and fill Azure + Docker values.
2. Create an Azure resource group, App Service plan, and Web App (see scripts/create_azure_resources.sh).
3. Create a service principal and add the JSON to the GitHub secret AZURE_CREDENTIALS.
4. Add secrets: KEY_VAULT_NAME, RESOURCE_GROUP, WEBAPP_NAME, DOCKERHUB_USERNAME, DOCKERHUB_TOKEN.
5. Push to GitHub to trigger the workflow .github/workflows/azure-container-deploy.yml.

See README_AZURE.md for end-to-end setup.
