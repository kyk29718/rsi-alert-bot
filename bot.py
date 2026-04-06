import ccxt
import pandas as pd
import requests
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================
# 🔐 TELEGRAM CONFIG
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("⚠️ BOT_TOKEN or CHAT_ID missing in environment variables!")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
        if res.status_code != 200:
            print("❌ Telegram Error:", res.text)
        else:
            print("✅ Sent:", msg)
    except Exception as e:
        print("📡 Telegram Exception:", e)

# ==============================
# ⚙️ SETTINGS
# ==============================
symbol = 'BTC/USDT'
timeframe = '15m'
RSI_PERIOD = 14
TARGET_POINTS = 200

exchange = ccxt.binance({'options': {'defaultType': 'future'}})

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

    # Send startup message
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
        df['rsi'] = rsi(df, RSI_PERIOD)
        price = df['close'].iloc[-2]
        curr_rsi = df['rsi'].iloc[-2]
        send_telegram(f"🚀 RSI Bot Started!\nPrice: {price}\nRSI: {round(curr_rsi,2)}")
    except Exception as e:
        print("Startup fetch error:", e)
        send_telegram("⚠️ RSI Bot started but failed to fetch initial price!")

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, RSI_PERIOD)

            # Use last closed candle
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

            print(f"⏰ Candle Closed | Price: {price} | RSI: {round(curr_rsi,2)}")

            # LONG
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"🚀 LONG SIGNAL\nPrice: {price}\nSL: {low}\nTarget: {price + TARGET_POINTS}\nRSI: {round(curr_rsi,2)}"
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"🔻 SHORT SIGNAL\nPrice: {price}\nSL: {high}\nTarget: {price - TARGET_POINTS}\nRSI: {round(curr_rsi,2)}"
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(15)

# ==============================
# 🌐 KEEP ALIVE SERVER
# ==============================
def keep_alive():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")
        def log_message(self, format, *args):
            return

    port = int(os.environ.get("PORT", 10000))  # Render port
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ Web Server running on port {port}")
    server.serve_forever()

# ==============================
# 🚀 START BOTH THREADS
# ==============================
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()

    # Keep main thread alive
    while True:
        time.sleep(60)
