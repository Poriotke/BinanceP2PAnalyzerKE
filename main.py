import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
TOKEN = '8711420378:AAH7Z2LlLLhso-DTViWGA6diBkqbgMf55TM'

# Set up logging to track errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_live_kes_rate():
    """Fetches real-time KES/USD exchange rate."""
    try:
        # Using a reliable free API for currency rates
        r = requests.get("https://open.er-api.com/v6/latest/USD")
        data = r.json()
        return data['rates'].get('KES', 129.0)  # Default fallback
    except Exception as e:
        logging.error(f"Error fetching FX rate: {e}")
        return 129.0

async def fetch_binance_p2p(pay_type_name, pay_type_id):
    """Core logic to scrape Binance P2P and calculate insights."""
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }
    
    payload = {
        "asset": "USDT",
        "fiat": "KES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [pay_type_id],
        "rows": 5,
        "tradeType": "BUY" # Showing prices to BUY USDT
    }

    current_fx_rate = get_live_kes_rate()

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        output = [
            f"🇰🇪 *Kenya P2P: {pay_type_name}*",
            f"📈 *Global USD/KES:* {current_fx_rate:.2f}\n"
        ]
        
        if not data.get('data'):
            return "No active ads found for this payment method."

        for ad in data['data']:
            if ad['adv'].get('isPromoted'): 
                continue
            
            price = float(ad['adv']['price'])
            name = ad['advertiser']['nickName']
            
            # Calculate Premium (Markup over the official exchange rate)
            usd_equiv = price / current_fx_rate
            premium = ((price / current_fx_rate) - 1) * 100
            
            output.append(f"💰 *{price:,.2f} KES* (~${usd_equiv:.2f})")
            output.append(f"📊 Premium: +{premium:.2f}%")
            output.append(f"👤 `{name}`\n")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}"

# --- TELEGRAM COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇰🇪 *Binance Kenya P2P Bot Analyzer*\n\n"
        "Use the commands below to check live USDT rates:\n"
        "/mpesa - Check Safaricom M-Pesa\n"
        "/bank - Check Bank Transfers (Equity/KCB/etc)\n"
        "/airtel - Check Airtel Money\n"
        "/compare - See all spreads side-by-side"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def mpesa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Fetching M-Pesa rates...")
    result = await fetch_binance_p2p("M-Pesa", "M-Pesa-Kenya")
    await update.message.reply_text(result, parse_mode='Markdown')

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Fetching Bank Transfer rates...")
    result = await fetch_binance_p2p("Bank Transfer", "BankTransfer")
    await update.message.reply_text(result, parse_mode='Markdown')

async def airtel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Fetching Airtel Money rates...")
    result = await fetch_binance_p2p("Airtel Money", "AirtelMoney")
    await update.message.reply_text(result, parse_mode='Markdown')

async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Comparing all markets...")
    m = await fetch_binance_p2p("M-Pesa", "M-Pesa-Kenya")
    b = await fetch_binance_p2p("Bank", "BankTransfer")
    await update.message.reply_text(f"{m}\n---\n{b}", parse_mode='Markdown')

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Register Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mpesa", mpesa))
    application.add_handler(CommandHandler("bank", bank))
    application.add_handler(CommandHandler("airtel", airtel))
    application.add_handler(CommandHandler("compare", compare))
    
    print("Bot is polling...")
    application.run_polling()
    
