import requests
import json
import os

def fetch_serper(topic):
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SERPER_API_KEY topilmadi")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{topic} haqida", "gl": "uz"})
    headers = {
      'X-API-KEY': api_key,
      'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
    res = response.json()
    snippets = []
    if 'knowledgeGraph' in res and 'description' in res['knowledgeGraph']:
        snippets.append(res['knowledgeGraph']['description'])
    if 'organic' in res:
        for item in res['organic'][:3]:
            if 'snippet' in item:
                snippets.append(item['snippet'])
    return snippets

print(fetch_serper("Toshkent metro tarixi"))
