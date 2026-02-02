 import os
import telebot
from flask import Flask
from threading import Thread

# Configuración desde variables de entorno
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID', '6667062973')

# Verificar token
if not TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN no configurado")
    print("💡 Configura la variable TELEGRAM_TOKEN en Railway")
    exit(1)

# Inicializar bot
bot = telebot.TeleBot(TOKEN)
print(f"✅ Bot inicializado: @{bot.get_me().username}")

# Comando básico de prueba
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    name = message.from_user.first_name
    response = f"""
🎉 ¡Hola {name}!

🤖 *Gold USDT Bot*
✅ *Bot funcionando correctamente*

💰 *Características:*
• Bono diario de 0.3 USDT
• Sistema de referidos
• Retiros desde 5 USDT

👑 *Admin ID:* {ADMIN_ID}
"""
    bot.reply_to(message, response, parse_mode='Markdown')

# Comando admin
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if str(message.from_user.id) == ADMIN_ID:
        bot.reply_to(message, "👑 *Panel Admin activo*\n\n✅ Todo funciona correctamente", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ No tienes permisos")

# Servidor web básico para Railway
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>Gold USDT Bot</title></head>
        <body style="text-align:center; padding:50px; background:#667eea; color:white;">
            <h1>🤖 Gold USDT Bot</h1>
            <p>✅ Bot activo y funcionando</p>
            <p>🌐 Alojado en Railway.app</p>
            <a href="https://t.me/Gojld_bot" style="background:white; color:#667eea; padding:15px 30px; border-radius:25px; text-decoration:none; font-weight:bold;">Usar el Bot</a>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

# Función principal
def main():
    print("🚀 Iniciando Gold Bot en Railway...")
    print(f"🤖 Token configurado: {'Sí' if TOKEN else 'No'}")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    # Iniciar Flask en hilo separado
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False), daemon=True)
    flask_thread.start()
    print("🌐 Servidor web iniciado en puerto 8080")
    
    # Iniciar bot de Telegram
    print("🤖 Iniciando polling del bot...")
    print("✅ ¡Bot listo! Envía /start a @Gojld_bot")
    bot.polling(none_stop=True, timeout=60)

if __name__ == '__main__':
    main()