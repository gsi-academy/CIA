import requests

try:
    res = requests.get("http://127.0.0.1:8000/api/v1/health")
    print(f"Status: {res.status_code}")
    print(f"Content-Type: {res.headers.get('Content-Type')}")
    print(f"Body: {res.text}")
except Exception as e:
    print(f"Error: {e}")
