 
   import os
import telebot
from flask import Flask
from threading import Thread

# Configuración
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8519041982:AAG9y3iaC9S9nk2bOo5rkI1-OMcXgsavG2o')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6667062973))

# Inicializar bot
bot = telebot.TeleBot(TOKEN)

# Datos en memoria (simple)
users = {}

# Comandos
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    user_id = str(user.id)
    
    if user_id not in users:
        users[user_id] = {
            'balance': 0.3,  # Bono inicial
            'name': user.first_name
        }
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn1 = telebot.types.InlineKeyboardButton("💰 Saldo", callback_data='balance')
    btn2 = telebot.types.InlineKeyboardButton("🎁 Bono Diario", callback_data='daily')
    btn3 = telebot.types.InlineKeyboardButton("💸 Cómo ganar", callback_data='how')
    btn4 = telebot.types.InlineKeyboardButton("🎫 Retirar", callback_data='withdraw')
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.reply_to(message, 
                f"🎉 ¡Hola {user.first_name}!\n\n🤖 *Gold USDT Bot*\n✅ Bot funcionando en Koyeb\n\nElige una opción:",
                reply_markup=markup,
                parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    
    if call.data == 'balance':
        balance = users.get(user_id, {}).get('balance', 0)
        bot.answer_callback_query(call.id, f"Saldo: {balance:.2f} USDT")
    
    elif call.data == 'daily':
        users[user_id]['balance'] = round(users[user_id].get('balance', 0) + 0.3, 2)
        bot.answer_callback_query(call.id, "✅ ¡Bono diario de 0.3 USDT!")
    
    elif call.data == 'how':
        bot.answer_callback_query(call.id, "🎁 Bono diario: 0.3 USDT\n👥 Referidos: 0.05 USDT")
    
    elif call.data == 'withdraw':
        bot.answer_callback_query(call.id, "📧 Contacta al admin para retirar")

# Servidor web
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Gold Bot activo en Koyeb"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Main
if __name__ == '__main__':
    print("🚀 Bot iniciando en Koyeb...")
    
    # Iniciar Flask en hilo separado
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print(f"🤖 Bot: @{bot.get_me().username}")
    print("✅ Bot listo!")
    
    bot.polling(none_stop=True)