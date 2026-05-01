import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. HEARTBEAT SERVER (For Render Free Tier) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is Online", 200

def run_web_app():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- 2. UPDATED BINANCE LOGIC ---
def get_live_fx_rate():
    try:
        # Fetching current USD/KES rate
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
        "asset": "USDT", 
        "fiat": "KES", 
        "merchantCheck": False,
        "page": 1, 
        "payTypes": [method_id], 
        "rows": 10, # Increased rows to filter promoted ads better
        "tradeType": "BUY"
    }

    current_fx = get_live_fx_rate()
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15).json()
        
        if not res.get('data'):
            return f"❌ No ads found for *{method_name}*.\nID Used: `{method_id}`"

        output = [f"🇰🇪 *{method_name} Market*\n📈 *FX:* 1 USD = {current_fx:.2f} KES\n"]
        
        count = 0
        for ad in res['data']:
            # Skip promoted/scammy ads and limit to top 5 real ads
            if ad['adv'].get('isPromoted') or count >= 5: continue
            
            price = float(ad['adv']['price'])
            premium = ((price / current_fx) - 1) * 100
            name = ad['advertiser']['nickName']
            
            output.append(f"💰 *{price:,.2f} KES* (~${price/current_fx:.2f})")
            output.append(f"📊 Premium: +{premium:.2f}% | 👤 `{name}`\n")
            count += 1
            
        return "\n".join(output) if count > 0 else "❌ No non-promoted ads found."
    except Exception:
        return "⚠️ Binance connection timed out. Retry."

# --- 3. TELEGRAM COMMANDS ---
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🇰🇪 *Binance P2P Analyzer(P.o.Riot🍄)*\n/mpesa - Safaricom M-Pesa\n/bank - All Banks\n/compare - M-Pesa vs Bank", parse_mode='Markdown')

async def mpesa_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(await fetch_p2p_data("M-Pesa", "MPesaKenya"), parse_mode='Markdown')

async def bank_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text(await fetch_p2p_data("Bank", "BankTransfer"), parse_mode='Markdown')

async def compare_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    m = await fetch_p2p_data("M-Pesa", "MPesaKenya")
    b = await fetch_p2p_data("Bank", "BankTransfer")
    await u.message.reply_text(f"{m}\n---\n{b}", parse_mode='Markdown')

# --- 4. START ---
if __name__ == '__main__':
    threading.Thread(target=run_web_app, daemon=True).start()
    TOKEN = os.environ.get('BOT_TOKEN')
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mpesa", mpesa_cmd))
    app.add_handler(CommandHandler("bank", bank_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.run_polling()
    
