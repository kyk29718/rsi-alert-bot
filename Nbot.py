import ccxt
import pandas as pd
import requests
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================
# 🔐 TELEGRAM (ENV VARIABLES)
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Debug prints to confirm env variables
print("BOT_TOKEN:", BOT_TOKEN)
print("CHAT_ID:", CHAT_ID)

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ CONFIG ERROR: BOT_TOKEN or CHAT_ID is missing from Render Environment Variables.")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg}  # removed parse_mode to avoid Markdown errors
        res = requests.post(url, data=payload)
        
        # Log response for debugging
        if res.status_code == 200:
            print(f"✅ Telegram: Message sent successfully to {CHAT_ID}")
        else:
            print(f"❌ Telegram Failed! Status: {res.status_code}")
            print(f"📝 Response from Telegram: {res.text}")
            print(f"💡 Tip: If it says 'chat not found', your Group ID might need a minus sign (e.g., -100...)")
            
    except Exception as e:
        print(f"📡 Connection Error: Could not reach Telegram API: {e}")

# ==============================
# ⚙️ SETTINGS
# ==============================
symbol = 'BTC/USDT'
timeframe = '15m'
RSI_PERIOD = 14
TARGET_POINTS = 200

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

# ==============================
# 📊 RSI CALCULATION
# ==============================
def rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ==============================
# 🔁 BOT CORE LOOP
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    print("🚀 Strategy Engine Started.")
    send_telegram("🚀 RSI Alert Bot Initialized\nMonitoring BTC/USDT 15m")

    while True:
        print(f"⏰ Heartbeat: {time.strftime('%H:%M:%S')} - Checking Market...")

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, RSI_PERIOD)

            candle_time = df['time'].iloc[-2]

            if candle_time == last_candle_time:
                time.sleep(30)
                continue

            last_candle_time = candle_time
            
            prev_rsi = df['rsi'].iloc[-3]
            curr_rsi = df['rsi'].iloc[-2]
            price = df['close'].iloc[-2]
            high = df['high'].iloc[-2]
            low = df['low'].iloc[-2]

            print(f"📊 Candle Closed | Price: {price} | RSI: {round(curr_rsi, 2)}")

            # --- RSI Cross Logic ---
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"🚀 LONG SIGNAL\nPrice: {price}\nSL: {low}\nTarget: {price + TARGET_POINTS}"
                send_telegram(msg)
                last_signal = "LONG"

            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"🔻 SHORT SIGNAL\nPrice: {price}\nSL: {high}\nTarget: {price - TARGET_POINTS}"
                send_telegram(msg)
                last_signal = "SHORT"

            # Optional: alive ping every loop
            send_telegram("✅ Bot Alive Check")  # remove later if spam

            time.sleep(30)

        except Exception as e:
            print(f"❌ Loop Error: {e}")
            time.sleep(15)

# ==============================
# 🌐 WEB SERVER (HEALTH CHECK)
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running')

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Web Server Port: {port}")
    server.serve_forever()

# ==============================
# 🏁 EXECUTION
# ==============================
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    run_bot()
