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
# IMPORTANT: Set 'BOT_TOKEN' and 'CHAT_ID' in Render's "Environment" tab
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram Config Missing: Check Render Environment Variables")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print(f"📡 Telegram Sync: {res.status_code}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

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

    print("🚀 Starting RSI Strategy Engine...")
    send_telegram("🚀 RSI Alert Bot is now LIVE on Render")

    while True:
        # This print helps you see the bot is "alive" in Render logs
        print(f"⏰ Heartbeat: {time.strftime('%H:%M:%S')} - Checking Market...")

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, RSI_PERIOD)

            # Analyze the most recently CLOSED candle
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

            # --- SIGNAL LOGIC ---
            
            # LONG: RSI crosses UP through 50
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = (f"🚀 **LONG SIGNAL**\n\n"
                       f"Price: {price}\n"
                       f"SL: {low}\n"
                       f"Target: {price + TARGET_POINTS}\n"
                       f"RSI: {round(curr_rsi, 2)}")
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT: RSI crosses DOWN through 50
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = (f"🔻 **SHORT SIGNAL**\n\n"
                       f"Price: {price}\n"
                       f"SL: {high}\n"
                       f"Target: {price - TARGET_POINTS}\n"
                       f"RSI: {round(curr_rsi, 2)}")
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)

        except Exception as e:
            print(f"❌ API/Logic Error: {e}")
            time.sleep(15)

# ==============================
# 🌐 WEB SERVER (RENDER HEALTH)
# ==============================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Bot is Running')

    def do_HEAD(self):
        # Fixes the 501 Unsupported Method error from Render
        self.send_response(200)
        self.end_headers()

    # Silence the log messages for every health check to keep logs clean
    def log_message(self, format, *args):
        return

def keep_alive():
    # Use the port Render provides, or 10000 as fallback
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Web Server Internal Port: {port}")
    server.serve_forever()

# ==============================
# 🏁 EXECUTION
# ==============================
if __name__ == "__main__":
    # Start the web server in the background
    web_server = threading.Thread(target=keep_alive, daemon=True)
    web_server.start()
    
    # Start the trading bot in the foreground
    run_bot()
