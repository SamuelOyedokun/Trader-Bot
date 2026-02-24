from flask import Flask, request, jsonify
from bot.message_handler import handle_message
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Meta calls this to verify your webhook is real
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    return "Forbidden", 403

# Twilio calls this every time a user sends a message
@app.route("/webhook", methods=["POST"])
def receive_message():
    try:
        print("=== WEBHOOK HIT ===")
        print("Form data:", request.form)
        print("Raw data:", request.data)
        
        phone_number = request.form.get("From", "").replace("whatsapp:+", "")
        text = request.form.get("Body", "")

        print(f"Phone: {phone_number}")
        print(f"Text: {text}")

        if phone_number and text:
            handle_message(phone_number, text)
        else:
            print("No phone or text found")
    except Exception as e:
        print(f"Error: {e}")
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>', 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)