import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. HEARTBEAT SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Online", 200

def run_web_app():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- 2. LOGIC ---
def get_live_fx_rate():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        return r.json()['rates'].get('KES', 130.0)
    except:
        return 130.0

async def fetch_p2p_data(method_name, method_id):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    payload = {
        "asset": "USDT", "fiat": "KES", "merchantCheck": False,
        "page": 1, "payTypes": [method_id], "rows": 10, "tradeType": "BUY"
    }
    current_fx = get_live_fx_rate()
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15).json()
        if not res.get('data') or len(res['data']) == 0:
            return f"❌ No ads found for {method_name}"
        
        output = [f"🇰🇪 *{method_name} Market*\n📈 *FX:* 1 USD = {current_fx:.2f} KES\n"]
        count = 0
        for ad in res['data']:
            if ad['adv'].get('isPromoted') or count >= 3: continue 
            price = float(ad['adv']['price'])
            prem = ((price / current_fx) - 1) * 100
            output.append(f"💰 *{price:,.2f} KES* | +{prem:.2f}%")
            count += 1
        return "\n".join(output)
    except:
        return "⚠️ Connection error."

# --- 3. COMMANDS ---
async def start(u, c):
    welcome_text = (
        "**🇰🇪 BINANCE KENYA P2P ANALYZER**\n\n"
        "**Available Commands:**\n"
        "**/Bot by P.o.Riot🍄**\n"
        "**/mpesa - Safaricom M-Pesa**\n"
        "**/airtel - Airtel Money**\n"
        "**/kcb - KCB Bank**\n"
        "**/equity - Equity Bank**\n"
        "**/im - I&M Bank**\n"
        "**/compare - Full Market Comparison**"
    )
    await u.message.reply_text(welcome_text, parse_mode='Markdown')

async def mpesa_cmd(u, c):
    await u.message.reply_text(await fetch_p2p_data("M-Pesa", "MPesaKenya"), parse_mode='Markdown')

async def airtel_cmd(u, c):
    await u.message.reply_text(await fetch_p2p_data("Airtel Money", "AirtelMoney"), parse_mode='Markdown')

async def kcb_cmd(u, c):
    await u.message.reply_text(await fetch_p2p_data("KCB Bank", "KCB"), parse_mode='Markdown')

async def equity_cmd(u, c):
    await u.message.reply_text(await fetch_p2p_data("Equity Bank", "EquityBank"), parse_mode='Markdown')

async def im_cmd(u, c):
    # I&M often uses general BankTransfer tag if specific tag is empty
    res = await fetch_p2p_data("I&M Bank", "IMBank")
    if "❌" in res:
        res = await fetch_p2p_data("I&M (via Bank Transfer)", "BankTransfer")
    await u.message.reply_text(res, parse_mode='Markdown')

async def compare_cmd(u, c):
    await u.message.reply_text("🔄 Comparing all major Kenyan channels...")
    mpesa = await fetch_p2p_data("M-Pesa", "MPesaKenya")
    equity = await fetch_p2p_data("Equity", "EquityBank")
    kcb = await fetch_p2p_data("KCB", "KCB")
    
    await u.message.reply_text(f"{mpesa}\n\n---\n\n{equity}\n\n---\n\n{kcb}", parse_mode='Markdown')

# --- 4. EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_web_app, daemon=True).start()
    TOKEN = os.environ.get('BOT_TOKEN')
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mpesa", mpesa_cmd))
    app.add_handler(CommandHandler("airtel", airtel_cmd))
    app.add_handler(CommandHandler("kcb", kcb_cmd))
    app.add_handler(CommandHandler("equity", equity_cmd))
    app.add_handler(CommandHandler("im", im_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.run_polling()
    
