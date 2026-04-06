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

SYMBOL = "BTCUSD"
TIMEFRAME = "1m"
RSI_PERIOD = 14
BASE_URL = "https://api.india.delta.exchange"

# ==============================
# 📩 TELEGRAM SEND
# ==============================
def send_telegram(msg, chat_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=10)
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

# ==============================
# 📊 RSI CALCULATION
# ==============================
def calculate_rsi(df, period=14):
    delta = df['close'].astype(float).diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 0.00001)
    return 100 - (100 / (1 + rs))

# ==============================
# 📊 GET RSI (FOR COMMAND)
# ==============================
def get_latest_rsi():
    try:
        url = f"{BASE_URL}/v2/history/candles"
        params = {"symbol": SYMBOL, "resolution": TIMEFRAME, "limit": 100}

        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        result = data.get("result", [])

        if not result or len(result) < 20:
            return "❌ Not enough data"

        df = pd.DataFrame(result)
        df['time'] = pd.to_numeric(df['time'])
        df['close'] = pd.to_numeric(df['close'])
        df = df.sort_values('time')

        df['rsi'] = calculate_rsi(df, RSI_PERIOD)

        latest = df.iloc[-2]

        price = latest['close']
        rsi = round(latest['rsi'], 2)

        return f"📊 BTC RSI\nPrice: {price}\nRSI: {rsi}\nTF: {TIMEFRAME}"

    except Exception as e:
        return f"Error: {e}"

# ==============================
# 🤖 AUTO SIGNAL BOT
# ==============================
def run_bot():
    last_signal = None
    last_candle_time = None

    logging.info("🔥 Auto signal bot started")

    while True:
        try:
            url = f"{BASE_URL}/v2/history/candles"
            params = {"symbol": SYMBOL, "resolution": TIMEFRAME, "limit": 100}

            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            result = data.get("result", [])

            if not result or len(result) < 20:
                time.sleep(30)
                continue

            df = pd.DataFrame(result)
            df['time'] = pd.to_numeric(df['time'])
            df['close'] = pd.to_numeric(df['close'])
            df = df.sort_values('time')

            df['rsi'] = calculate_rsi(df, RSI_PERIOD)

            current = df.iloc[-2]
            previous = df.iloc[-3]

            if current['time'] == last_candle_time:
                time.sleep(20)
                continue

            last_candle_time = current['time']

            curr_rsi = round(current['rsi'], 2)
            prev_rsi = round(previous['rsi'], 2)
            price = current['close']

            logging.info(f"Price: {price} | RSI: {curr_rsi}")

            # IMPORTANT: send to YOUR group ID (set manually)
            GROUP_CHAT_ID = os.getenv("CHAT_ID")

            if prev_rsi < 50 <= curr_rsi and last_signal != "LONG":
                send_telegram(f"🟢 LONG\nPrice: {price}\nRSI: {curr_rsi}", GROUP_CHAT_ID)
                last_signal = "LONG"

            elif prev_rsi > 50 >= curr_rsi and last_signal != "SHORT":
                send_telegram(f"🔴 SHORT\nPrice: {price}\nRSI: {curr_rsi}", GROUP_CHAT_ID)
                last_signal = "SHORT"

        except Exception as e:
            logging.error(f"Loop Error: {e}")
            time.sleep(10)

        time.sleep(30)

# ==============================
# 🤖 TELEGRAM LISTENER (GROUP)
# ==============================
def listen_telegram():
    logging.info("🤖 Telegram listener started")

    last_update_id = None

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 30}

            if last_update_id:
                params["offset"] = last_update_id + 1

            res = requests.get(url, params=params, timeout=35)
            data = res.json()

            for update in data.get("result", []):
                last_update_id = update["update_id"]

                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")

                if not text:
                    continue

                logging.info(f"📩 {text} from {chat_id}")

                # ======================
                # /rsi COMMAND (GROUP SAFE)
                # ======================
                if "/rsi" in text.lower():
                    reply = get_latest_rsi()
                    send_telegram(reply, chat_id)

                # OPTIONAL: START BUTTON (works mainly in private)
                elif text.lower() == "/start":
                    keyboard = {
                        "keyboard": [[{"text": "📊 Get RSI"}]],
                        "resize_keyboard": True
                    }

                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "🤖 Bot Ready!",
                            "reply_markup": keyboard
                        }
                    )

                elif text == "📊 Get RSI":
                    reply = get_latest_rsi()
                    send_telegram(reply, chat_id)

        except Exception as e:
            logging.error(f"Listener Error: {e}")
            time.sleep(5)

# ==============================
# 🌐 FLASK
# ==============================
@app.route("/")
def home():
    return "Bot running 🚀"

# ==============================
# ▶️ MAIN
# ==============================
if __name__ == "__main__":
    logging.info("🚀 Starting bot...")

    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=listen_telegram, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
