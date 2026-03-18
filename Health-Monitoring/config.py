import streamlit as st
import os

def get_api_key():
    # 1. Try Streamlit secrets
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]

    # 2. Fallback to environment variable
    key = os.getenv("OPENAI_API_KEY")

    if not key:
        raise ValueError("OPENAI_API_KEY not found")

    return key