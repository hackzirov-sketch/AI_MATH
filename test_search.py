import urllib.request
from urllib.parse import quote
import re

def search(topic):
    url = f'https://html.duckduckgo.com/html/?q={quote(topic)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, flags=re.IGNORECASE|re.DOTALL)
    # clean tags
    cleaned = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
    return cleaned[:3]

print(search('Toshkent metro tarixi'))
