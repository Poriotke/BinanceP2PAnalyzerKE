import requests
import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. THE HEARTBEAT SERVER (To stay on Render Free Tier) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running!"

def run_web_app():
    # Render provides a PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- 2. THE BOT LOGIC ---
TOKEN = os.getenv('BOT_TOKEN')

def get_live_fx_rate():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        return r.json()['rates'].get('KES', 130.0)
    except:
        return 130.0

async def fetch_p2p(method_name, method_id):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": "USDT", "fiat": "KES", "merchantCheck": False,
        "page": 1, "payTypes": [method_id], "rows": 5, "tradeType": "BUY"
    }
    fx = get_live_fx_rate()
    try:
        res = requests.post(url, json=payload, timeout=10).json()
        output = [f"🇰🇪 *{method_name} Market*\n📈 *FX:* 1 USD = {fx:.2f} KES\n"]
        for ad in res.get('data', []):
            if ad['adv'].get('isPromoted'): continue
            p = float(ad['adv']['price'])
            prem = ((p / fx) - 1) * 100
            output.append(f"💰 *{p:,.2f} KES* (~${p/fx:.2f})\n📊 Premium: +{prem:.2f}%\n")
        return "\n".join(output)
    except:
        return "⚠️ Market busy. Try again."

async def mpesa(u, c):
    await u.message.reply_text(await fetch_p2p("M-Pesa", "M-Pesa-Kenya"), parse_mode='Markdown')

# --- 3. START EVERYTHING ---
if __name__ == '__main__':
    # Start the web server in a separate thread so it doesn't block the bot
    threading.Thread(target=run_web_app, daemon=True).start()
    
    # Start the bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("mpesa", mpesa))
    app.run_polling()
    
