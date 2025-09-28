import urllib.request
import json

try:
    with urllib.request.urlopen('http://localhost:8000/openapi.json') as response:
        data = json.loads(response.read().decode())
    paths = data.get('paths', {})
    for path, methods in paths.items():
        for method, details in methods.items():
            desc = details.get('summary', details.get('description', 'No description'))
            print(f"- {method.upper()} {path}: {desc}")
except Exception as e:
    print(f"Error fetching or parsing OpenAPI: {e}")