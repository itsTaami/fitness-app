import requests
import streamlit as st

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

def call_groq(prompt, model="llama-3.1-8b-instant", max_tokens=1600):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are a safe, supportive fitness & nutrition assistant. "
                "Give teen-friendly advice, no extreme diets, no medical claims."
            )},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    try:
        with st.spinner("Generating..."):
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"❌ Error {r.status_code}: {r.text}"
    except Exception as e:
        return f"❌ Request failed: {str(e)}"
