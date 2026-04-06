import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("BOT_TOKEN:", BOT_TOKEN)
print("CHAT_ID:", CHAT_ID)

if BOT_TOKEN and CHAT_ID:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": "✅ Telegram test message"}
    res = requests.post(url, data=payload)
    print("Telegram Response:", res.text)
else:
    print("⚠️ BOT_TOKEN or CHAT_ID missing")
