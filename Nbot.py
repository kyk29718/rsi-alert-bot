import ccxt
import pandas as pd
import requests
import time
import threading
import os

# ==============================
# 🔐 TELEGRAM (ENV VARIABLES)
# ==============================
BOT_TOKEN = os.getenv("8764213237:AAF9Ipslfo6wbTptG5f9SMXyHhS0FfGaZS0")
CHAT_ID = os.getenv("5939554496")

def send_telegram(msg):
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

    print("🚀 Bot started (console)")
    send_telegram("🚀 RSI Alert Bot Started")

    while True:
        print("🔁 Bot loop running...")   # DEBUG

        try:
            print("📡 Fetching data...")  # DEBUG
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

            print("RSI:", prev_rsi, "→", curr_rsi)  # DEBUG

            # ================= SIGNAL =================
            # LONG
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = f"""
🚀 LONG SIGNAL

Price: {price}
SL: {low}
Target: {price + TARGET_POINTS}
RSI: {round(curr_rsi,2)}
"""
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = f"""
🔻 SHORT SIGNAL

Price: {price}
SL: {high}
Target: {price - TARGET_POINTS}
RSI: {round(curr_rsi,2)}
"""
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(10)

# ==============================
# 🌐 KEEP ALIVE (FOR RENDER FREE)
# ==============================
def keep_alive():
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running')

    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

# ==============================
# 🚀 START (IMPORTANT FIX)
# ==============================
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    keep_alive()   # 👈 main thread runs server
