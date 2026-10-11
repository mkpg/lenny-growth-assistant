import httpx
import json

url = 'http://localhost:8000/api/v1/chat'
payload = {
    'question': 'According to Adam Fishman\'s episode "How to build a high-performing growth team," what are his key recommendations? Cite the actual episode URL and use only retrieved transcript evidence.',
    'provider': 'google',
    'model': 'gemini-3.5-flash'
}

print('Sending request to Gemini...')
try:
    with httpx.Client() as client:
        response = client.post(url, json=payload, timeout=60.0)
    print(f'Status Code: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print('Response Body:')
        print(json.dumps(data, indent=2))
    else:
        print('Error Response:')
        print(response.text)
except Exception as e:
    print(f'Request failed: {e}')
