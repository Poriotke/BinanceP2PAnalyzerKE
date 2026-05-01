import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. HEARTBEAT SERVER (Fixes Render "No Response" Issue) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Active", 200

def run_web_app():
    # Render assigns a dynamic port; the bot must listen to it to stay alive
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- 2. UPDATED BINANCE LOGIC ---
def get_live_fx_rate():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        return r.json()['rates'].get('KES', 130.0)
    except:
        return 130.0

async def fetch_p2p_data(method_name, method_id):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {"User-Agent": "Mozilla/5.0"}
    payload = {
        "asset": "USDT", 
        "fiat": "KES", 
        "merchantCheck": False,
        "page": 1, 
        "payTypes": [method_id], 
        "rows": 5, 
        "tradeType": "BUY"
    }

    current_fx = get_live_fx_rate()
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        if not res.get('data'): return f"No ads found for {method_name}."

        output = [f"🇰🇪 *{method_name} Market*\n📈 *FX:* 1 USD = {current_fx:.2f} KES\n"]
        for ad in res['data']:
            if ad['adv'].get('isPromoted'): continue
            price = float(ad['adv']['price'])
            premium = ((price / current_fx) - 1) * 100
            name = ad['advertiser']['nickName']
            output.append(f"💰 *{price:,.2f} KES* (~${price/current_fx:.2f})\n📊 Premium: +{premium:.2f}% | 👤 `{name}`\n")
        return "\n".join(output)
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- 3. TELEGRAM COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🇰🇪 *Binance Kenya P2P*\n/mpesa - Check Safaricom\n/bank - Check Banks\n/compare - Side-by-side", parse_mode='Markdown')

async def mpesa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await fetch_p2p_data("M-Pesa", "M-Pesa-Kenya"), parse_mode='Markdown')

async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await fetch_p2p_data("Bank", "BankTransfer"), parse_mode='Markdown')

# --- 4. START COMMAND ---
if __name__ == '__main__':
    # Start the web server in a background thread so Render sees the app as "Live"
    threading.Thread(target=run_web_app, daemon=True).start()
    
    # Start the Telegram Bot using the Environment Variable you created
    TOKEN = os.environ.get('BOT_TOKEN')
    if TOKEN:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("mpesa", mpesa_cmd))
        app.add_handler(CommandHandler("bank", bank_cmd))
        print("Bot is polling...")
        app.run_polling()
    else:
        print("Error: BOT_TOKEN not found!")
        
