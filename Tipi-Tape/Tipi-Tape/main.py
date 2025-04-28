import os
import logging
import asyncio
import feedparser
import threading
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== CONFIGURACIÓN ======
try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
except KeyError as e:
    logging.error("❌ Error: Configura BOT_TOKEN y CHAT_ID en Secrets")
    raise RuntimeError("Variables de entorno faltantes")

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ocultar logs sensibles de httpx
logging.getLogger("httpx").setLevel(logging.WARNING)


# Palabras clave y fuentes
PALABRAS_CLAVE = ['crypto', 'bitcoin', 'ethereum', 'web3', 'blockchain', 'airdrop']
FUENTES_RSS = [
    'https://decrypt.co/feed',
    'https://cointelegraph.com/rss',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
]

# Variables globales para control
noticias_enviadas = set()

# ====== FUNCIONES PRINCIPALES ======
def obtener_noticias():
    global noticias_enviadas
    noticias_filtradas = []

    for url in FUENTES_RSS:
        try:
            feed = feedparser.parse(url)
            if not hasattr(feed, 'entries') or not feed.entries:
                logging.warning(f"Feed vacío o sin entradas: {url}")
                continue

            contador_fuente = 0
            for entrada in feed.entries:
                if contador_fuente >= 2:  # Máximo 2 por fuente
                    break

                try:
                    enlace = entrada.get('link', '')
                    titulo = entrada.get('title', '').lower()
                    resumen = entrada.get('summary', '').lower()

                    # CORRECCIÓN DEL ERROR: Paréntesis bien balanceados
                    if (any(palabra in titulo or palabra in resumen for palabra in PALABRAS_CLAVE) 
                        and enlace not in noticias_enviadas):

                        noticia_formateada = f"📰 <a href='{enlace}'>{entrada.title}</a>"
                        noticias_filtradas.append(noticia_formateada)
                        noticias_enviadas.add(enlace)
                        contador_fuente += 1

                except Exception as e:
                    logging.error(f"Error procesando entrada: {str(e)}")
                    continue

        except Exception as e:
            logging.error(f"Error al parsear feed {url}: {str(e)}")
            continue

    return noticias_filtradas[:5]  # Límite global

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
    except Exception as e:
        logging.error(f"Error al enviar noticias: {str(e)}")

async def comando_noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        noticias = obtener_noticias()
        if noticias:
            mensaje = "📢 <b>Últimas noticias cripto</b>\n\n" + "\n\n".join(noticias)
            await update.message.reply_text(
                mensaje,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text("⚠️ No hay noticias relevantes disponibles ahora.")
    except Exception as e:
        logging.error(f"Error en comando /noticias: {str(e)}")
        await update.message.reply_text("❌ Ocurrió un error al obtener las noticias.")

# ====== CONFIGURACIÓN FLASK ======
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🤖 Bot de Noticias Cripto - Operativo"

# ====== INICIALIZACIÓN ======
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("noticias", comando_noticias))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(enviar_noticias_automaticas(application)),
        'cron',
        hour='8,13,20'
    )
    scheduler.start()

    application.run_polling()

if __name__ == '__main__':
    # Hilo para Flask
    threading.Thread(
        target=app_flask.run,
        kwargs={'host': '0.0.0.0', 'port': 8080},
        daemon=True
    ).start()

    # Iniciar bot principal
    try:
        main()
    except Exception as e:
        logging.error(f"Error fatal: {str(e)}")