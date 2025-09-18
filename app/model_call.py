# app/model_call.py

import os
import requests

MODEL_API_URL = os.getenv("MODEL_API_URL", "http://localhost:11434/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "phi2")  # or "llama3", etc.

def model_call(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a symbolic reasoning assistant inside the SignalZero system."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }

    response = requests.post(MODEL_API_URL, json=payload, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Model API failed: {response.status_code} - {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]
