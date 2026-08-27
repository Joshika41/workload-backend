import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from auth import create_access_token
from datetime import timedelta

# Create an ADMIN token
token = create_access_token(data={"sub": "admin", "role": "ADMIN", "faculty_id": ""}, expires_delta=timedelta(minutes=15))

headers = {
    "Authorization": f"Bearer {token}"
}

try:
    res = requests.post("http://127.0.0.1:8000/api/admin/generate-batch", headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
except Exception as e:
    print(f"Error: {e}")
