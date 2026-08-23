AI Data Workspace

This project is a multi-mode Streamlit application for working with uploaded data and AI-driven analysis. It supports three focused modes:

- Upload and Analyze: work with CSV, Excel, or PDF files, inspect data preview, view summary statistics, and interact with AI in a grounded data-analysis mode.
- SQL Explorer: query SQLite data, add rows manually, and bulk-import CSV/Excel files into the local database.
- General Assistant: answer broader questions using the current date, general knowledge, and a separate prompt template.

The app is designed to keep context focused instead of using one generic bot for everything. Separate prompt templates are used for data analysis, SQL analysis, and general knowledge questions.

Local quick start:

1. python -m pip install -r requirements.txt
2. python -m streamlit run app.py

GitHub → Azure CI/CD deployment:

This repository includes a GitHub Actions workflow for automatic deployment from GitHub to Azure App Service using Docker containers.

Workflow behavior:

1. Push to the `main` branch.
2. GitHub Actions authenticates to Azure and Docker Hub.
3. The app is containerized and published to Docker Hub.
4. The Azure Web App is updated to pull the latest image automatically.
5. App settings such as `OPENAI_API_KEY`, `WEBSITES_PORT`, and `SQLITE_DB_PATH` are configured automatically during deployment.

Required GitHub secrets:

- `AZURE_CREDENTIALS`
- `RESOURCE_GROUP`
- `WEBAPP_NAME`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `OPENAI_API_KEY`

Full Azure setup notes are in `README_AZURE.md`.
