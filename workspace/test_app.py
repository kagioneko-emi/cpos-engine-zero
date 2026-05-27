import requests
import ast

def fetch_data(url):
    # Fixed: added timeout to prevent hanging
    response = requests.get(url, timeout=10)
    return response.text

def unsafe_execution(user_input):
    # Fixed: use ast.literal_eval for safe evaluation of literals
    return ast.literal_eval(user_input)

if __name__ == "__main__":
    print(fetch_data("https://example.com"))
    # Changed from "1 + 1" to "2" as ast.literal_eval only supports literals
    print(unsafe_execution("2"))