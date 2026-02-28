from flask import Flask, request, jsonify
from bot.message_handler import handle_message
from bot.scheduler import start_scheduler
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Start the background scheduler
scheduler = start_scheduler()


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


# Meta calls this every time a user sends a message
@app.route("/webhook", methods=["POST"])
def receive_message():
    try:
        print("=== WEBHOOK HIT ===")
        data = request.get_json()
        print("Payload:", data)

        # Meta sends data in this nested structure
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        # Ignore status updates (delivered, read, sent) — only handle messages
        if "statuses" in value:
            return "OK", 200

        messages = value.get("messages", [])
        if not messages:
            return "OK", 200

        message = messages[0]
        msg_type = message.get("type")

        # Only handle text messages
        if msg_type != "text":
            print(f"Ignored non-text message type: {msg_type}")
            return "OK", 200

        phone = message.get("from", "")   # e.g. "2347032327482"
        text = message.get("text", {}).get("body", "").strip()

        print(f"Phone: {phone}")
        print(f"Text: {text}")

        if phone and text:
            handle_message(phone, text)
        else:
            print("No phone or text found")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

    return "OK", 200


# Health check endpoint
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "running",
        "scheduler": "active",
        "next_summary": "Every Sunday 8PM Nigeria time"
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)