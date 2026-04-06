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

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN or CHAT_ID missing")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
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
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# ==============================
# 📊 RSI FUNCTION (FIXED)
# ==============================
def rsi(data, period=14):
    delta = data['close'].diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ==============================
# 🔁 BOT LOOP (FIXED)
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    print("🚀 Bot started...")
    send_telegram("🚀 RSI Bot Started")

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)

            df = pd.DataFrame(ohlcv, columns=[
                'time','open','high','low','close','volume'
            ])

            df['rsi'] = rsi(df, RSI_PERIOD)

            # Convert time
            df['time'] = pd.to_datetime(df['time'], unit='ms')

            # Use last CLOSED candle
            candle_time = df['time'].iloc[-2]

            if candle_time == last_candle_time:
                time.sleep(10)
                continue

            last_candle_time = candle_time

            prev_rsi = df['rsi'].iloc[-3]
            curr_rsi = df['rsi'].iloc[-2]

            price = df['close'].iloc[-2]
            high = df['high'].iloc[-2]
            low = df['low'].iloc[-2]

            print(f"⏱ {candle_time} | Price: {price} | RSI: {round(curr_rsi,2)}")

            # ======================
            # 🚀 LONG SIGNAL
            # ======================
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"""🚀 LONG SIGNAL

Price: {price}
SL: {low}
Target: {price + TARGET_POINTS}
RSI: {round(curr_rsi,2)}
"""
                send_telegram(msg)
                last_signal = "LONG"

            # ======================
            # 🔻 SHORT SIGNAL
            # ======================
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"""🔻 SHORT SIGNAL

Price: {price}
SL: {high}
Target: {price - TARGET_POINTS}
RSI: {round(curr_rsi,2)}
"""
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(10)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(5)

# ==============================
# 🌐 HEALTH SERVER (FIXED)
# ==============================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"🌐 Server running on port {port}")
    server.serve_forever()

# ==============================
# 🚀 MAIN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    run_bot()
