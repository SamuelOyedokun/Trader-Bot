import requests
import sys

# Get message from command line or use default
message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "hello"

print(f"\n📤 Sending: '{message}'")
print("─" * 40)

response = requests.post(
    "http://127.0.0.1:5000/webhook",
    data={
        "From": "whatsapp:+2347032327482",
        "Body": message
    }
)
print(f"Status: {response.status_code}")