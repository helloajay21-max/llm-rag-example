import truststore
truststore.inject_into_ssl()

from openai import OpenAI
from config import get_api_key

client = OpenAI(api_key=get_api_key())


def generate_insights(summary):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a health analytics expert."},
            {"role": "user", "content": f"Analyze this data:\n{summary}"}
        ],
        temperature=0.5
    )
    return response.choices[0].message.content


def chat_with_ai(messages):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5
    )
    return response.choices[0].message.content