import requests
import time

BASE_URL = "http://127.0.0.1:5000/webhook"
PHONE = "whatsapp:+2347032327482"

messages = [
    "show top products",
    "show top customers",
    "sales chart",
    "switch to drinks",
    "I buy 20 cans malt 300 each",
    "I sell 5 cans malt 500, I buy am 300",
    "drinks summary",
    "switch to food",
    "food summary",
    "show all sections",
    "show drinks stock",
    "show food stock",
    "subscribe",
    "I don finish the goods, start fresh",
    "abcdefgh random text",
]

def send_message(msg):
    response = requests.post(BASE_URL, data={"From": PHONE, "Body": msg})
    return response.status_code

print("=" * 50)
print("🤖 TRADERBOT LOCAL TEST")
print("=" * 50)
print("Watch the Flask terminal for bot replies\n")

for msg in messages:
    print(f"📤 Sending: {msg}")
    status = send_message(msg)
    print(f"   Server status: {status}")
    print()
    time.sleep(2)  # Wait 2 seconds between messages

print("=" * 50)
print("✅ All messages sent. Check Flask terminal for replies.")
print("=" * 50)