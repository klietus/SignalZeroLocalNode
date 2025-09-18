# app/model_call.py

import os
import requests

MODEL_API_URL = os.getenv("MODEL_API_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b-text-q5_K_M")

def model_call(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "num_predict": 48
    }
    print("sending: " + prompt)
    response = requests.post(MODEL_API_URL, json=payload, timeout=300)

    if response.status_code != 200:
        raise RuntimeError(f"Model API failed: {response.status_code} - {response.text}")

    data = response.json()
    print("received:" + data["response"])
    return data["response"]
