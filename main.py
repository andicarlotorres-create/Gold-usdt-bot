 import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
import telebot
from telebot import types
from threading import Thread

# ===== CONFIGURACIÓN =====
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8519041982:AAG9y3iaC9S9nk2bOo5rkI1-OMcXgsavG2o')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6667062973))
DAILY_BONUS = 0.3
REFERRAL_BONUS = 0.05
MIN_WITHDRAWAL = 5.0

# ===== INICIAR BOT =====
bot = telebot.TeleBot(TOKEN)

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
@bot.message_handler(commands=['start'])
def start_command(message):
    user = message.from_user
    user_id = str(user.id)
    user_data = get_user(user_id)
    user_data['username'] = user.username or user.first_name
    
    # Sistema de referidos
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id != user_id:
            referrer_data = get_user(referrer_id)
            if user_id not in referrer_data['referrals']:
                referrer_data['referrals'].append(user_id)
                referrer_data['balance'] = round(referrer_data['balance'] + REFERRAL_BONUS, 2)
                update_user(referrer_id, referrer_data)
    
    update_user(user_id, user_data)
    
    # Crear teclado
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💰 Saldo", callback_data='balance')
    btn2 = types.InlineKeyboardButton("💸 Cómo ganar", callback_data='how')
    btn3 = types.InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')
    btn4 = types.InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.send_message(
        message.chat.id,
        f"🎉 ¡Hola {user.first_name}!\n\n🤖 *Gold - USDT Bot*\n\n*Gana USDT gratis cada día*\n\nElige una opción:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    user_data = get_user(user_id)
    
    if call.data == 'balance':
        text = f"💰 *Saldo:* {user_data['balance']:.2f} USDT\n👥 *Referidos:* {len(user_data['referrals'])}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menú", callback_data='menu'))
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    elif call.data == 'how':
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        text = f"""
*💸 CÓMO GANAR USDT:*

1. 🎁 *Bono Diario:* {DAILY_BONUS} USDT cada 24h
2. 👥 *Referidos:* {REFERRAL_BONUS} USDT por cada amigo
3. 📈 *Multiplica:* Cada referido te da {REFERRAL_BONUS} USDT

*🔗 Tu enlace de referidos:*
`{ref_link}`
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menú", callback_data='menu'))
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    elif call.data == 'withdraw':
        balance = user_data['balance']
        if balance < MIN_WITHDRAWAL:
            text = f"❌ *Saldo insuficiente*\n\n💰 *Mínimo para retirar:* {MIN_WITHDRAWAL} USDT\n💳 *Tu saldo:* {balance:.2f} USDT"
        else:
            text = f"✅ *¡Puedes retirar!*\n\n💰 *Saldo disponible:* {balance:.2f} USDT\n\n📧 *Contacta al administrador:* @admin_gold"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menú", callback_data='menu'))
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    elif call.data == 'daily':
        last_bonus = user_data.get('last_daily')
        now = datetime.now()
        
        if last_bonus:
            last_date = datetime.fromisoformat(last_bonus)
            if now - last_date < timedelta(hours=24):
                horas_restantes = 24 - (now - last_date).total_seconds() / 3600
                horas = int(horas_restantes)
                minutos = int((horas_restantes - horas) * 60)
                text = f"⏰ *Ya reclamaste hoy*\n\n🕒 *Próximo bono en:* {horas}h {minutos}m"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Menú", callback_data='menu'))
                bot.edit_message_text(
                    text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
                return
        
        # Dar bono
        user_data['balance'] = round(user_data['balance'] + DAILY_BONUS, 2)
        user_data['last_daily'] = now.isoformat()
        update_user(user_id, user_data)
        
        text = f"✅ *¡Bono diario de {DAILY_BONUS} USDT!*\n\n💰 *Nuevo saldo:* {user_data['balance']:.2f} USDT"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menú", callback_data='menu'))
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    elif call.data == 'menu':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💰 Saldo", callback_data='balance')
        btn2 = types.InlineKeyboardButton("💸 Cómo ganar", callback_data='how')
        btn3 = types.InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')
        btn4 = types.InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')
        markup.add(btn1, btn2, btn3, btn4)
        bot.edit_message_text(
            "🤖 *Gold - USDT Bot*\n\n*Elige una opción:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = str(message.from_user.id)
    if int(user_id) != ADMIN_ID:
        bot.reply_to(message, "❌ No tienes permisos de administrador")
        return
    
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0] or 0.0
    conn.close()
    
    text = f"""
👑 *PANEL ADMINISTRADOR*

🤖 *Bot:* @{bot.get_me().username}
📊 *Usuarios totales:* {total_users}
💰 *Saldo total en sistema:* {total_balance:.2f} USDT
👨‍💼 *Admin ID:* {ADMIN_ID}
"""
    bot.reply_to(message, text, parse_mode='Markdown')

# ===== SERVIDOR WEB PARA RENDER =====
web_app = Flask(__name__)

@web_app.route('/')
def home():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    conn.close()
    return f"""
    <html>
        <head>
            <title>Gold USDT Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 15px; backdrop-filter: blur(10px); }}
                h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
                .btn {{ display: inline-block; padding: 12px 30px; background: white; color: #764ba2; text-decoration: none; border-radius: 25px; font-weight: bold; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Gold USDT Bot</h1>
                <p>Bot activo y funcionando 24/7</p>
                <p>Usuarios registrados: {total_users}</p>
                <p>🌐 Bot alojado en Render.com</p>
                <a href="https://t.me/Gojld_bot" class="btn">🚀 Usar el Bot en Telegram</a>
            </div>
        </body>
    </html>
    """

@web_app.route('/health')
def health():
    return "OK", 200

# ===== MAIN =====
def run_flask():
    web_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def main():
    print("🚀 Iniciando Gold Bot...")
    print(f"🤖 Bot: Gold (@Gojld_bot)")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    init_db()
    
    # Iniciar servidor web en segundo plano
    print("🌐 Iniciando servidor web...")
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print("🤖 Configurando bot de Telegram...")
    print("✅ Bot inicializado correctamente")
    print("📊 Bot funcionando 24/7 en Render.com")
    print("🎉 ¡El bot está listo para usar! Visita: https://t.me/Gojld_bot")
    
    # Iniciar el bot
    bot.polling(none_stop=True, timeout=60)

if __name__ == '__main__':
    main()