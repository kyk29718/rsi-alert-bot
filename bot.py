import requests
import pandas as pd
import time
import threading
import os
from flask import Flask

# ==============================
# 🌐 FLASK APP (FOR RENDER)
# ==============================
app = Flask(__name__)

# ==============================
# 🔐 CONFIGURATION
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "BTCUSD"                      # Spot BTC/USD
TIMEFRAME = "1m"                       # Use 1m for testing (change later to 15m)
RSI_PERIOD = 14
BASE_URL = "https://api.india.delta.exchange"

# ==============================
# 📩 TELEGRAM FUNCTION
# ==============================
def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Missing BOT_TOKEN or CHAT_ID")
        return

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )

        data = res.json()
        if not data.get("ok"):
            print("❌ Telegram Error:", data)

    except Exception as e:
        print("📡 Telegram Exception:", e)

# ==============================
# 📊 RSI CALCULATION
# ==============================
def calculate_rsi(df, period=14):
    delta = df['close'].astype(float).diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss.replace(0, 0.00001)
    return 100 - (100 / (1 + rs))

# ==============================
# 🤖 BOT LOGIC
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    print(f"🚀 Spot BTC RSI Bot Started ({SYMBOL})")
    send_telegram(f"🚀 Spot BTC RSI Bot Started!\nSymbol: {SYMBOL}\nTF: {TIMEFRAME}")

    while True:
        try:
            print("\n📡 Fetching candles...")

            url = f"{BASE_URL}/v2/history/candles"
            params = {
                "symbol": SYMBOL,
                "resolution": TIMEFRAME,
                "limit": 100
            }

            response = requests.get(url, params=params, timeout=15)

            print("Status Code:", response.status_code)

            data = response.json()
            print("API Response (short):", str(data)[:200])

            result = data.get("result", [])

            # ❌ No data
            if not result:
                print("❌ No candle data received")
                time.sleep(30)
                continue

            # ❌ Not enough data
            if len(result) < 20:
                print("❌ Not enough data for RSI")
                time.sleep(30)
                continue

            # ======================
            # DATA PROCESSING
            # ======================
            df = pd.DataFrame(result)
            df['time'] = pd.to_numeric(df['time'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.sort_values('time')

            df['rsi'] = calculate_rsi(df, RSI_PERIOD)

            # Use closed candles only
            current_candle = df.iloc[-2]
            previous_candle = df.iloc[-3]

            candle_time = current_candle['time']

            # Avoid duplicate processing
            if candle_time == last_candle_time:
                print("⏳ Waiting for new candle...")
                time.sleep(20)
                continue

            last_candle_time = candle_time

            curr_rsi = round(current_candle['rsi'], 2)
            prev_rsi = round(previous_candle['rsi'], 2)
            price = current_candle['close']

            print(f"⏰ Candle Closed | Price: {price} | RSI: {curr_rsi}")

            # ======================
            # 📈 STRATEGY (RSI 50 CROSS)
            # ======================

            # LONG
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = (f"🟢 LONG SIGNAL\n"
                       f"Price: {price}\n"
                       f"RSI: {curr_rsi}\n"
                       f"TF: {TIMEFRAME}")
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = (f"🔴 SHORT SIGNAL\n"
                       f"Price: {price}\n"
                       f"RSI: {curr_rsi}\n"
                       f"TF: {TIMEFRAME}")
                send_telegram(msg)
                last_signal = "SHORT"

        except Exception as e:
            print("❌ Loop Error:", e)
            time.sleep(15)

        time.sleep(30)

# ==============================
# 🌐 FLASK ROUTES
# ==============================
@app.route("/")
def home():
    return "BTC Spot RSI Bot is Running 🚀", 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200

# ==============================
# ▶️ MAIN
# ==============================
if __name__ == "__main__":
    print("🚀 Starting Flask + RSI Bot...")

    # Start bot in background
    threading.Thread(target=run_bot, daemon=True).start()

    # Start Flask server
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
