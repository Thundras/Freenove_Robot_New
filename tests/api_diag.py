import requests
import time

try:
    print("Testing local API connectivity...")
    res = requests.post("http://127.0.0.1:5000/api/pose/sit", timeout=2)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
except Exception as e:
    print(f"Error: {e}")
