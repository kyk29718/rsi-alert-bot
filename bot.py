import requests
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==============================
# 🔐 ENV VARIABLES (Render)
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ==============================
# 📩 SEND MESSAGE
# ==============================
def send_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": CHAT_ID,
            "text": message
        }
        response = requests.get(url, params=params)
        print("Telegram response:", response.json())
    except Exception as e:
        print("Error:", e)

# ==============================
# 🤖 BOT LOOP
# ==============================
def bot_loop():
    print("🚀 Bot started...")

    while True:
        try:
            print("Bot loop running...")

            send_message("🔥 Bot is LIVE on Render!")

            time.sleep(60)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(10)

# ==============================
# 🌐 KEEP RENDER ALIVE
# ==============================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

# ==============================
# ▶️ START BOTH THREADS
# ==============================
if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    run_server()
