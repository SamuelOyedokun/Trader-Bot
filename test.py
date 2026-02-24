import requests
response = requests.post(
    "http://127.0.0.1:5000/webhook",
    data={
        "From": "whatsapp:+2347032327482",
        "Body": "I sell 5 bags rice 45000 each, I buy am 38000"
    }
)
print("Status:", response.status_code)
print("Response:", response.text)
