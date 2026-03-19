from openai import OpenAI
from azure_config import OPENAI_API_KEY, MODEL_NAME

client = OpenAI(api_key=OPENAI_API_KEY)

def get_llm_response(prompt):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Answer based on context only."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content