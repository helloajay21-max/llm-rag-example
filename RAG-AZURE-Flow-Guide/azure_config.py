from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

KV_URL = "Put Your Azure URL"

credential = DefaultAzureCredential()
client = SecretClient(vault_url=KV_URL, credential=credential)

def get_secret(name):
    return client.get_secret(name).value

OPENAI_API_KEY = get_secret("openai-api-key")

MODEL_NAME = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
