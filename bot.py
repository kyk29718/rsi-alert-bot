import requests
import pandas as pd
import time
import threading
import os
import logging
from flask import Flask

# ==============================
# 🔧 LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

# ==============================
# 🔐 CONFIG
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "BTCUSD"
TIMEFRAME = "15m"
RSI_PERIOD = 14
EMA_PERIOD = 50
TARGET_POINTS = 200

# ✅ FIXED API
BASE_URL = "https://api.delta.exchange"

# ==============================
# 📩 TELEGRAM
# ==============================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

# ==============================
# 📊 INDICATORS
# ==============================
def calculate_rsi(df):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(RSI_PERIOD).mean()
    rs = gain / loss.replace(0, 0.00001)
    return 100 - (100 / (1 + rs))

def calculate_ema(df):
    return df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()

# ==============================
# 🤖 BOT
# ==============================
def run_bot():
    last_signal = None
    last_time = None

    logging.info("🔥 Smart Trade Bot Started")
    send_telegram("🚀 Smart Trade Bot Started (15m TF)")

    while True:
        try:
            url = f"{BASE_URL}/v2/history/candles"
            params = {
                "symbol": SYMBOL,
                "resolution": TIMEFRAME,
                "limit": 200
            }

            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            result = data.get("result", [])

            # ✅ DEBUG
            logging.info(f"Candle count: {len(result)}")

            if not result or len(result) < 50:
                logging.warning("Not enough data for signals")
                time.sleep(30)
                continue

            df = pd.DataFrame(result)
            df['time'] = pd.to_numeric(df['time'])
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df = df.sort_values('time')

            # Indicators
            df['rsi'] = calculate_rsi(df)
            df['ema'] = calculate_ema(df)

            current = df.iloc[-2]
            previous = df.iloc[-3]

            if current['time'] == last_time:
                time.sleep(20)
                continue

            last_time = current['time']

            price = current['close']
            rsi = round(current['rsi'], 2)
            prev_rsi = previous['rsi']
            ema = round(current['ema'], 2)

            prev_high = previous['high']
            prev_low = previous['low']

            logging.info(f"Price: {price} | RSI: {rsi} | EMA: {ema}")

            # ======================
            # 🟢 LONG
            # ======================
            if (
                prev_rsi < 45 and rsi >= 50 and
                price > ema and
                last_signal != "LONG"
            ):
                entry = round(price, 2)
                target = round(price + TARGET_POINTS, 2)
                sl = round(prev_low, 2)

                msg = (
                    f"🟢 LONG TRADE\n\n"
                    f"Entry: {entry}\n"
                    f"Target: {target}\n"
                    f"Stop Loss: {sl}\n\n"
                    f"RSI: {rsi} | EMA: {ema}\n"
                    f"TF: {TIMEFRAME}"
                )

                send_telegram(msg)
                last_signal = "LONG"

            # ======================
            # 🔴 SHORT
            # ======================
            elif (
                prev_rsi > 55 and rsi <= 50 and
                price < ema and
                last_signal != "SHORT"
            ):
                entry = round(price, 2)
                target = round(price - TARGET_POINTS, 2)
                sl = round(prev_high, 2)

                msg = (
                    f"🔴 SHORT TRADE\n\n"
                    f"Entry: {entry}\n"
                    f"Target: {target}\n"
                    f"Stop Loss: {sl}\n\n"
                    f"RSI: {rsi} | EMA: {ema}\n"
                    f"TF: {TIMEFRAME}"
                )

                send_telegram(msg)
                last_signal = "SHORT"

        except Exception as e:
            logging.error(f"Loop Error: {e}")
            time.sleep(10)

        time.sleep(30)

# ==============================
# 🌐 FLASK
# ==============================
@app.route("/")
def home():
    return "Smart Trading Bot Running 🚀"

# ==============================
# ▶️ MAIN
# ==============================
if __name__ == "__main__":
    logging.info("🚀 Starting bot...")

    threading.Thread(target=run_bot, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
