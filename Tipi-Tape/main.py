import os
import logging
import asyncio
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== CONFIGURACIÓN ======
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Render usa getenv() para variables
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    logging.error("❌ Error: Configura BOT_TOKEN y CHAT_ID en Render (Environment Variables)")
    exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce logs de HTTP

# Palabras clave y fuentes RSS
PALABRAS_CLAVE = ['crypto', 'bitcoin', 'ethereum', 'web3', 'blockchain', 'airdrop']
FUENTES_RSS = [
    'https://decrypt.co/feed',
    'https://cointelegraph.com/rss',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
]
noticias_enviadas = set()  # Almacena enlaces para evitar duplicados

# ====== FUNCIONES PRINCIPALES ======
def obtener_noticias():
    global noticias_enviadas
    noticias_filtradas = []

    for url in FUENTES_RSS:
        try:
            feed = feedparser.parse(url)
            if not hasattr(feed, 'entries') or not feed.entries:
                logging.warning(f"Feed vacío: {url}")
                continue

            contador_fuente = 0
            for entrada in feed.entries:
                if contador_fuente >= 2:  # Límite de 2 noticias por fuente
                    break

                enlace = entrada.get('link', '')
                titulo = entrada.get('title', '').lower()
                resumen = entrada.get('summary', '').lower()

                if (any(palabra in titulo or palabra in resumen for palabra in PALABRAS_CLAVE)
                    and enlace not in noticias_enviadas:

                    noticia_formateada = f"📰 <a href='{enlace}'>{entrada.title}</a>"
                    noticias_filtradas.append(noticia_formateada)
                    noticias_enviadas.add(enlace)
                    contador_fuente += 1

        except Exception as e:
            logging.error(f"Error al parsear {url}: {str(e)}")

    return noticias_filtradas[:5]  # Máximo 5 noticias por ejecución

async def enviar_noticias_automaticas(app):
    try:
        noticias = obtener_noticias()
        if noticias:
            mensaje = "🚀 <b>Últimas noticias cripto</b>\n\n" + "\n\n".join(noticias)
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=mensaje,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logging.info("✅ Noticias enviadas automáticamente")
    except Exception as e:
        logging.error(f"Error al enviar noticias: {str(e)}")

async def comando_noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        noticias = obtener_noticias()
        if noticias:
            mensaje = "📢 <b>Últimas noticias cripto</b>\n\n" + "\n\n".join(noticias)
            await update.message.reply_text(
                text=mensaje,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("⚠️ No hay noticias nuevas ahora.")
    except Exception as e:
        logging.error(f"Error en /noticias: {str(e)}")
        await update.message.reply_text("❌ Error al obtener noticias")

# ====== INICIALIZACIÓN ======
def main():
    # Configura el bot de Telegram
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("noticias", comando_noticias))

    # Programa el envío automático (8AM, 1PM, 8PM UTC)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(enviar_noticias_automaticas(application)),
        'cron',
        hour='8,13,20'
    )
    scheduler.start()

    # Inicia el bot en modo polling
    logging.info("🤖 Bot iniciado (Polling)...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.critical(f"❌ Error fatal: {str(e)}")
