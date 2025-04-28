from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

# --- Flask setup para mantener Replit activo ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot activo"

# --- Comando /noticias ---
async def noticias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📰 Aquí van las noticias importantes del día.")

# --- Función para inicializar el bot ---
async def start_bot():
    TOKEN = os.environ['BOT_TOKEN']
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("noticias", noticias_command))

    print("✅ Bot corriendo 24/7...")

    # Ejecutamos el bot sin cerrar el loop
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
# --- Scheduler para Flask ---
def run_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()

# --- Lanzamos todo ---
def main():
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())  # Iniciamos bot en el mismo loop
    run_scheduler()
    app_flask.run(host="0.0.0.0", port=8080)

if __name__ == '__main__':
    main()
