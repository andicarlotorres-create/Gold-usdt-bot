import os
import json
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

def get_all_users():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(balance) FROM users")
    result = c.fetchone()
    conn.close()
    return result[0] or 0, result[1] or 0.0

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(
        f"🎉 ¡Hola {user.first_name}!\n\n🤖 *Gold - USDT Bot*\n\n*Gana USDT gratis cada día*\n\nElige una opción:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = get_user(user_id)
    
    if query.data == 'balance':
        text = f"💰 *Saldo:* {user_data['balance']:.2f} USDT\n👥 *Referidos:* {len(user_data['referrals'])}"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'how':
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = f"""
*💸 CÓMO GANAR USDT:*

1. 🎁 *Bono Diario:* {DAILY_BONUS} USDT cada 24h
2. 👥 *Referidos:* {REFERRAL_BONUS} USDT por cada amigo
3. 📈 *Multiplica:* Cada referido te da {REFERRAL_BONUS} USDT

*🔗 Tu enlace de referidos:*
`{ref_link}`
"""
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'withdraw':
        balance = user_data['balance']
        if balance < MIN_WITHDRAWAL:
            text = f"❌ *Saldo insuficiente*\n\n💰 *Mínimo para retirar:* {MIN_WITHDRAWAL} USDT\n💳 *Tu saldo:* {balance:.2f} USDT"
        else:
            text = f"✅ *¡Puedes retirar!*\n\n💰 *Saldo disponible:* {balance:.2f} USDT\n\n📧 *Contacta al administrador:* @admin_gold"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'daily':
        last_bonus = user_data.get('last_daily')
        now = datetime.now()
        
        if last_bonus:
            last_date = datetime.fromisoformat(last_bonus)
            if now - last_date < timedelta(hours=24):
                horas_restantes = 24 - (now - last_date).total_seconds() / 3600
                text = f"⏰ *Ya reclamaste hoy*\n\nVuelve en {horas_restantes:.1f} horas"
                keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                return
        
        # Dar bono
        user_data['balance'] = round(user_data['balance'] + DAILY_BONUS, 2)
        user_data['last_daily'] = now.isoformat()
        update_user(user_id, user_data)
        
        text = f"✅ *¡Bono diario de {DAILY_BONUS} USDT!*\n\n💰 *Nuevo saldo:* {user_data['balance']:.2f} USDT"
        keyboard = [[InlineKeyboardButton("🔙 Menú", callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("💰 Saldo", callback_data='balance')],
            [InlineKeyboardButton("💸 Cómo ganar", callback_data='how')],
            [InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')],
            [InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')]
        ]
        await query.edit_message_text(
            "🤖 *Gold - USDT Bot*\n\n*Elige una opción:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ===== COMANDO ADMIN =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if int(user_id) != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permisos de administrador")
        return
    
    total_users, total_balance = get_all_users()
    bot_info = await context.bot.get_me()
    
    text = f"""
👑 *PANEL ADMINISTRADOR*

🤖 *Bot:* @{bot_info.username}
📊 *Usuarios totales:* {total_users}
💰 *Saldo total en sistema:* {total_balance:.2f} USDT
👨‍💼 *Admin ID:* {ADMIN_ID}
"""
    await update.message.reply_text(text, parse_mode='Markdown')

# ===== SERVIDOR WEB PARA RENDER =====
web_app = Flask(__name__)

@web_app.route('/')
def home():
    total_users, total_balance = get_all_users()
    return f"""
    <html>
        <head>
            <title>Gold USDT Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 15px; backdrop-filter: blur(10px); }}
                h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
                .stats {{ background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; margin: 20px 0; }}
                .btn {{ display: inline-block; padding: 12px 30px; background: white; color: #764ba2; text-decoration: none; border-radius: 25px; font-weight: bold; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Gold USDT Bot</h1>
                <p>Bot activo y funcionando 24/7</p>
                <div class="stats">
                    <h3>📊 Estadísticas en tiempo real:</h3>
                    <p>👥 Usuarios: {total_users}</p>
                    <p>💰 Saldo total: {total_balance:.2f} USDT</p>
                </div>
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
def main():
    print("🚀 Iniciando Gold Bot...")
    print(f"🤖 Bot: Gold (@Gojld_bot)")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    init_db()
    
    # Verificar token
    if not TOKEN or TOKEN == 'TU_TOKEN_AQUI':
        print("❌ ERROR: No se encontró TELEGRAM_TOKEN")
        print("💡 Configura la variable de entorno TELEGRAM_TOKEN en Render.com")
        return
    
    # Iniciar servidor web en segundo plano
    print("🌐 Iniciando servidor web...")
    web_thread = Thread(target=lambda: web_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False), daemon=True)
    web_thread.start()
    
    # Configurar bot de Telegram
    print("🤖 Configurando bot de Telegram...")
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot inicializado correctamente")
    print("🌐 Servidor web: http://0.0.0.0:8080")
    print("📊 Bot funcionando 24/7 en Render.com")
    print("🎉 ¡El bot está listo para usar! Visita: https://t.me/Gojld_bot")
    
    app_bot.run_polling()

if __name__ == '__main__':
    main()
