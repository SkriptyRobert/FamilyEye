import requests
import sys

# Change this to a valid token from your database (PairingToken table)
TOKEN = "REPLACE_WITH_ACTUAL_TOKEN"
API_URL = "http://localhost:8000/api/devices/pairing/status/" + TOKEN
# Need a valid JWT token too if we want to bypass auth, but wait...
# We can't easily get a valid JWT without logging in.

# Let's try to hit it without auth to see if we get 401 (Prove Auth is enabled)
try:
    print(f"Testing URL: {API_URL}")
    response = requests.get(API_URL, verify=False)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
