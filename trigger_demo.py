import requests
import time
import sys

BASE_URL = "https://127.0.0.1:8080"

def trigger_fix_demo():
    print("[*] Triggering Autonomous Fix Demo (via HTTPS)...")
    payload = {
        "action": "opened",
        "issue": {
            "title": "Fix ZeroDivisionError in workspace/test_app.py",
            "body": "The application crashes when the denominator is zero."
        }
    }
    try:
        # verify=False for self-signed certificates in local demo
        res = requests.post(f"{BASE_URL}/webhook", json=payload, verify=False)
        print(f"[+] Response: {res.json()}")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    trigger_fix_demo()
