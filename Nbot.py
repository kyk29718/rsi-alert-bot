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
# Fetching by KEY name. Ensure these keys are set in Render's dashboard.
BOT_TOKEN = os.getenv("8764213237:AAF9Ipslfo6wbTptG5f9SMXyHhS0FfGaZS0")
CHAT_ID = os.getenv("5939554496")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or CHAT_ID not set in Environment Variables")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("Telegram Response:", res.text)
    except Exception as e:
        print("Telegram Error:", e)

# ==============================
# ⚙️ SETTINGS
# ==============================
symbol = 'BTC/USDT'
timeframe = '15m'
RSI_PERIOD = 14
TARGET_POINTS = 200

exchange = ccxt.binance({
    'options': {'defaultType': 'future'}
})

# ==============================
# 📊 RSI FUNCTION
# ==============================
def rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ==============================
# 🔁 BOT LOOP
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    print("🚀 Bot logic started...")
    send_telegram("🚀 RSI Alert Bot Started")

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, RSI_PERIOD)

            # Use only CLOSED candle
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

            print(f"Candle closed at {price}. RSI: {round(curr_rsi, 2)}")

            # LONG Signal
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"🚀 LONG SIGNAL\n\nPrice: {price}\nSL: {low}\nTarget: {price + TARGET_POINTS}\nRSI: {round(curr_rsi,2)}"
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT Signal
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"🔻 SHORT SIGNAL\n\nPrice: {price}\nSL: {high}\nTarget: {price - TARGET_POINTS}\nRSI: {round(curr_rsi,2)}"
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)

        except Exception as e:
            print("❌ Bot Loop Error:", e)
            time.sleep(10)

# ==============================
# 🌐 WEB SERVER (RENDER HEALTH CHECK)
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is active')

    def do_HEAD(self):
        # This fixes the "501 Unsupported method ('HEAD')" error
        self.send_response(200)
        self.end_headers()

def keep_alive():
    # Render provides a PORT env variable; default to 10000 if not found
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health check server listening on port {port}")
    server.serve_forever()

# ==============================
# 🚀 MAIN ENTRY
# ==============================
if __name__ == "__main__":
    # Start the web server in a background thread
    web_thread = threading.Thread(target=keep_alive, daemon=True)
    web_thread.start()
    
    # Start the bot in the main thread
    run_bot()
