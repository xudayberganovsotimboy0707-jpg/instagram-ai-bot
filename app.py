import os
import requests
from flask import Flask, request, jsonify
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "aibot_uz_verify_123")

client = genai.Client(api_key=GEMINI_API_KEY)
app = Flask(__name__)

def ask_gemini(user_text: str) -> str:
    prompt = (
        "Siz Instagram sahifasining foydali, muloyim va qisqa javob beruvchi AI yordamchisiz. "
        "Foydalanuvchi qaysi tilda yozsa, o'sha tilda (asosan o'zbek tilida) tabiiy va aniq javob bering.\n\n"
        f"Foydalanuvchi xabari: {user_text}"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return (response.text or "Kechirasiz, hozircha javob bera olmadim.").strip()

def send_instagram_message(recipient_id: str, message_text: str):
    if not INSTAGRAM_ACCESS_TOKEN:
        print("INSTAGRAM_ACCESS_TOKEN kiritilmagan")
        return
    url = "https://graph.instagram.com/v21.0/me/messages"
    params = {"access_token": INSTAGRAM_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text[:1000]},
    }
    resp = requests.post(url, params=params, json=payload, timeout=15)
    print("Instagram javob statusi:", resp.status_code, resp.text)

@app.route("/", methods=["GET"])
def home():
    return "Instagram AI Bot 24/7 ishlamoqda!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message", {})
            text = message.get("text")

            if sender_id and text and not message.get("is_echo"):
                ai_reply = ask_gemini(text)
                send_instagram_message(sender_id, ai_reply)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
