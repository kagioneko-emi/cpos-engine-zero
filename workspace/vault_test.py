import requests

# 危険: APIキーを直接書いている
# Fetch from Vault
    import os
    from hvac import Client
    # Note: Use the project standard vault access method
    api_key = os.getenv("STRIPE_API_KEY") # Or actual vault call: client.secrets.kv.v2.read_secret_version(...)

def call_service():
    url = f"https://api.example.com/data?key={api_key}"
    # 危険: タイムアウトなし
    return requests.get(url, timeout=10).json()
