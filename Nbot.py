import ccxt
import pandas as pd
import requests
import time
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==============================
# 🔐 CONFIGURATION (RENDER ENV)
# ==============================
# Ensure these match the KEYS in your Render Dashboard -> Environment tab
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") 

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ SETUP ERROR: BOT_TOKEN or CHAT_ID not found in Environment Variables.")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # HTML mode is more stable for bots than Markdown
        payload = {
            "chat_id": CHAT_ID, 
            "text": msg, 
            "parse_mode": "HTML"
        }
        res = requests.post(url, data=payload)
        
        if res.status_code == 200:
            print(f"✅ Telegram: Message sent to {CHAT_ID}")
        else:
            print(f"❌ Telegram Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"📡 Connection Error: {e}")

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
# 🔁 TRADING ENGINE (POLLING)
# ==============================
def run_bot():
    symbol = 'BTC/USDT'
    timeframe = '15m'
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    
    last_signal = None
    last_candle_time = None

    print("🚀 Strategy Engine Active. Monitoring BTC/USDT...")
    send_telegram("<b>🤖 Bot Online</b>\nMonitoring 15m RSI Signals.")

    while True:
        # Heartbeat log to show Render the bot is still looping
        print(f"⏰ Heartbeat: {time.strftime('%H:%M:%S')} - Checking Market...")

        try:
            # Fetch last 100 candles
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
            df['rsi'] = rsi(df, 14)

            # Analyze the last CLOSED candle (index -2)
            candle_time = df['time'].iloc[-2]

            if candle_time == last_candle_time:
                time.sleep(30) # Wait 30 seconds before polling again
                continue

            last_candle_time = candle_time
            
            prev_rsi = df['rsi'].iloc[-3]
            curr_rsi = df['rsi'].iloc[-2]
            price = df['close'].iloc[-2]
            high = df['high'].iloc[-2]
            low = df['low'].iloc[-2]

            print(f"📊 Candle Close: {price} | RSI: {round(curr_rsi, 2)}")

            # --- SIGNAL LOGIC ---
            # LONG: RSI crosses UP through 50
            if prev_rsi < 50 and curr_rsi >= 50 and last_signal != "LONG":
                msg = (f"🚀 <b>LONG SIGNAL</b>\n\n"
                       f"Price: {price}\n"
                       f"SL: {low}\n"
                       f"Target: {price + 200}\n"
                       f"RSI: {round(curr_rsi, 2)}")
                send_telegram(msg)
                last_signal = "LONG"

            # SHORT: RSI crosses DOWN through 50
            elif prev_rsi > 50 and curr_rsi <= 50 and last_signal != "SHORT":
                msg = (f"🔻 <b>SHORT SIGNAL</b>\n\n"
                       f"Price: {price}\n"
                       f"SL: {high}\n"
                       f"Target: {price - 200}\n"
                       f"RSI: {round(curr_rsi, 2)}")
                send_telegram(msg)
                last_signal = "SHORT"

            time.sleep(30)

        except Exception as e:
            print(f"❌ Loop Error: {e}")
            time.sleep(20)

# ==============================
# 🌐 WEB SERVER (RENDER HEALTH)
# ==============================
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Active')

    def do_HEAD(self):
        # This prevents the 501 Unsupported Method error on Render
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return # Keeps logs clean by not printing every health check

def keep_alive():
    # Use the port assigned by Render
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheck)
    print(f"✅ Web Health Check listening on port {port}")
    server.serve_forever()

# ==============================
# 🏁 MAIN START
# ==============================
if __name__ == "__main__":
    # Start web server in background thread
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # Start bot loop in main thread
    run_bot()
