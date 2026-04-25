import os
import requests
import json

# Load keys from environment (comma-separated for multiple keys)
if __name__ == "__main__":
    keys_str = os.getenv("GEMINI_API_KEYS", "")
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]

    if not keys:
        print("Error: GEMINI_API_KEYS not set in environment")
        exit(1)

    api_key = keys[0]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": "hi"}]}]
    }
    headers = {"Content-Type": "application/json"}

    res = requests.post(url, headers=headers, json=payload)
    print("Status Code:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)
