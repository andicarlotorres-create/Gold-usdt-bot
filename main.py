import os
import json
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from flask import Flask
from threading import Thread

# ===== CONFIGURACIÓN =====
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8519041982:AAG9y3iaC9S9nk2bOo5rkI1-OMcXgsavG2o')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6667062973))
DAILY_BONUS = 0.3
REFERRAL_BONUS = 0.05
MIN_WITHDRAWAL = 5.0

# ===== BASE DE DATOS SQLite =====
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY,
                  balance REAL DEFAULT 0.0,
                  referrals TEXT DEFAULT '[]',
                  last_daily TEXT,
                  username TEXT)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    user_id = str(user_id)
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    
    if user:
        data = {
            'balance': user[1],
            'referrals': json.loads(user[2]),
            'last_daily': user[3],
            'username': user[4]
        }
    else:
        data = {
            'balance': 0.0,
            'referrals': [],
            'last_daily': None,
            'username': ''
        }
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    
    conn.close()
    return data

def update_user(user_id, data):
    user_id = str(user_id)
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''UPDATE users 
                 SET balance = ?, referrals = ?, last_daily = ?, username = ?
                 WHERE user_id = ?''',
              (data['balance'], 
               json.dumps(data['referrals']), 
               data['last_daily'], 
               data['username'],
               user_id))
    conn.commit()
    conn.close()

# ===== HANDLERS =====
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    user_data = get_user(user_id)
    user_data['username'] = user.username or user.first_name
    
    # Sistema de referidos
    if context.args:
        referrer_id = context.args[0]
        if referrer_id != user_id:
            referrer_data = get_user(referrer_id)
            if user_id not in referrer_data['referrals']:
                referrer_data['referrals'].append(user_id)
                referrer_data['balance'] = round(referrer_data['balance'] + REFERRAL_BONUS, 2)
                update_user(referrer_id, referrer_data)
    
    update_user(user_id, user_data)
    
    # Teclado
    keyboard = [
        [InlineKeyboardButton("💰 Saldo", callback_data='balance')],
        [InlineKeyboardButton("💸 Cómo ganar", callback_data='how')],
        [InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')],
        [InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"🎉 ¡Hola {user.first_name}!\n\n🤖 *Gold USDT Bot*\n\nElige una opción:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    
    if query.data == 'balance':
        text = f"💰 *Saldo:* {user_data['balance']:.2f} USDT\n👥 *Referidos:* {len(user_data['referrals'])}"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'how':
        bot = context.bot
        ref_link = f"https://t.me/{bot.username}?start={user_id}"
        text = f"""
💸 *CÓMO GANAR:*

1. 🎁 *Bono Diario:* {DAILY_BONUS} USDT
2. 👥 *Referidos:* {REFERRAL_BONUS} USDT c/u
3. 🔗 *Tu enlace:* {ref_link}
        """
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'withdraw':
        balance = user_data['balance']
        if balance < MIN_WITHDRAWAL:
            text = f"❌ *Saldo insuficiente*\n\n💰 Necesitas: {MIN_WITHDRAWAL} USDT\n📊 Tienes: {balance:.2f} USDT"
        else:
            text = f"✅ *¡Puedes retirar!*\n\n💰 Saldo: {balance:.2f} USDT\n📧 Contacta al admin"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'daily':
        last_bonus = user_data.get('last_daily')
        now = datetime.now()
        
        if last_bonus:
            last_date = datetime.fromisoformat(last_bonus)
            if now - last_date < timedelta(hours=24):
                horas_restantes = 24 - (now - last_date).total_seconds() / 3600
                text = f"⏰ *Ya reclamaste hoy*\n\nVuelve en {horas_restantes:.1f} horas"
                keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
                query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                return
        
        # Dar bono
        user_data['balance'] = round(user_data['balance'] + DAILY_BONUS, 2)
        user_data['last_daily'] = now.isoformat()
        update_user(user_id, user_data)
        
        text = f"✅ *¡Bono de {DAILY_BONUS} USDT!*\n\n💰 Nuevo saldo: {user_data['balance']:.2f} USDT"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("💰 Saldo", callback_data='balance')],
            [InlineKeyboardButton("💸 Cómo ganar", callback_data='how')],
            [InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')],
            [InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')]
        ]
        query.edit_message_text(
            text="🤖 *Gold USDT Bot - Menú*\n\nElige una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def admin(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if int(user_id) != ADMIN_ID:
        update.message.reply_text("❌ No tienes permisos de administrador")
        return
    
    text = f"""
👑 *PANEL ADMIN*

🤖 *Bot:* @{context.bot.username}
👨‍💼 *Admin ID:* {ADMIN_ID}
    """
    update.message.reply_text(text, parse_mode='Markdown')

# ===== SERVIDOR WEB PARA RENDER =====
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Gold Bot está funcionando!"

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ===== MAIN =====
def main():
    print("🚀 Iniciando Gold Bot...")
    
    # Iniciar servidor web
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # Configurar bot
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot listo: @Gojld_bot")
    print("📊 Bot funcionando 24/7 en Render.com")
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
