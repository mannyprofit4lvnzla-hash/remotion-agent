import os
import glob
import random
import time
import logging
import asyncio
from typing import List
from uuid import uuid4

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

from utils.google_drive import download_file_from_google_drive, download_folder_from_google_drive
from video_engine import create_inspirational_video, get_video_duration

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Configuration ---
BOT_TOKEN = os.environ.get("SECRET_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("SECRET_GEMINI_API_KEY")

VOL_PATH = "/tmp" 
MUSIC_DIR = os.path.join(VOL_PATH, "music")
os.makedirs(MUSIC_DIR, exist_ok=True)

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None
    logger.warning("GEMINI_API_KEY not set")

# --- Helpers ---

async def generate_quotes(keyword: str, count: int = 3) -> List[str]:
    if not gemini_client:
        return [f"Inspírate con {keyword}"] * count
        
    prompt = f"Genera {count} frases inspiradoras cortas (máximo 15 palabras) en español sobre el tema: '{keyword}'. Devuélvelas en formato de lista plana, una por línea."
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text
        lines = [line.strip().lstrip('- ').lstrip('1. ') for line in text.split('\n') if line.strip()]
        return lines[:count]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return [f"Inspírate con {keyword}"] * count

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_msg = (
        "👋 **¡Hola! Soy tu Bot de Inspiración V3 (MoviePy)**\n\n"
        "🎵 **Primero:** Importa tu música mandando:\n"
        "`/importmusic https://drive.google.com/drive/folders/...`\n\n"
        "🎥 **Luego:** Crea videos desde Google Drive mandando:\n"
        "`https://drive.google.com/file/d/... PalabraClave`"
    )
    await update.message.reply_markdown(welcome_msg)

async def import_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /importmusic <link_google_drive_folder>")
        return
        
    url = context.args[0]
    chat_id = update.message.chat_id
    
    await update.message.reply_text("🎵 Iniciando importación de música (esto puede tardar unos minutos)...")
    
    # Run heavy IO in background
    def do_download():
        download_folder_from_google_drive(url, MUSIC_DIR)
        return len(glob.glob(os.path.join(MUSIC_DIR, "**", "*.*"), recursive=True))
        
    try:
        loop = asyncio.get_running_loop()
        count = await loop.run_in_executor(None, do_download)
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Importación completada. Ahora tienes {count} canciones.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error importando música: {e}")

async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    chat_id = update.message.chat_id
    
    parts = text.split(maxsplit=1)
    url = parts[0]
    keyword = parts[1] if len(parts) > 1 else "Inspiración"
    
    if "drive.google.com" not in url and "youtube.com" not in url and "youtu.be" not in url:
        return # Ignore random text
        
    if "drive/folders/" in url:
        await update.message.reply_markdown(
            "❌ **¡Atención! Me enviaste un enlace de CARPETA.**\n\n"
            "🎵 Si lo que quieres es **importar música**, debes escribir el comando antes:\n"
            f"`/importmusic {url}`\n\n"
            "🎥 Si quieres **crear un video**, el enlace debe ser directo a un **archivo de video** específico, no a una carpeta."
        )
        return
        
    await update.message.reply_text(f"🚀 Iniciando proceso para '{keyword}'...\n1. Descargando video fuente...")
    
    timestamp = int(time.time())
    source_video_path = os.path.join(VOL_PATH, f"source_{chat_id}_{timestamp}.mp4")
    
    # 1. Download Video
    def do_download_vid():
        download_file_from_google_drive(url, source_video_path)
    
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, do_download_vid)
    except Exception as e:
        await update.message.reply_text(f"❌ Error descargando video: {str(e)}")
        return
        
    # 2. Get Quotes
    await update.message.reply_text("2. Generando frases motivacionales con Gemini...")
    quotes = await generate_quotes(keyword, count=3)
    
    # 3. Get Music
    music_files = []
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.flac"):
        music_files.extend(glob.glob(os.path.join(MUSIC_DIR, "**", ext), recursive=True))
        
    if not music_files:
        await update.message.reply_text("⚠️ No hay música en la librería. Usando modo silencio.")
        selected_musics = [None] * 3
    else:
        if len(music_files) >= 3:
            selected_musics = random.sample(music_files, 3)
        else:
            selected_musics = [random.choice(music_files) for _ in range(3)]
            
    # 4. Render
    await update.message.reply_text("3. Renderizando 3 videos nativamente en Python (sin Chromium)...")
    
    for i in range(3):
        quote = quotes[i] if i < len(quotes) else quotes[0]
        music_path = selected_musics[i]
        output_filename = f"output_{chat_id}_{timestamp}_{i+1}.mp4"
        output_path = os.path.join(VOL_PATH, output_filename)
        
        try:
            # Run heavy render in background thread to avoid freezing the bot loop
            def do_render():
                return create_inspirational_video(
                    source_video_path=source_video_path,
                    output_path=output_path,
                    quote=quote,
                    music_path=music_path,
                    target_duration=10
                )
            
            await update.message.reply_text(f"✏️ Renderizando clip {i+1}/3...")
            await loop.run_in_executor(None, do_render)
            
            # Send to Telegram
            with open(output_path, 'rb') as v_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=v_file,
                    caption=f"✨ Opción {i+1}\nFrase: {quote}"
                )
                
        except Exception as e:
            logger.error(f"Render {i+1} failed: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error renderizando clip {i+1}: {e}")

    await update.message.reply_text("✅ ¡Proceso 100% completado!")

# --- Main App ---

def main() -> None:
    if not BOT_TOKEN:
        logger.error("SECRET_BOT_TOKEN missing!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("importmusic", import_music))
    
    # Handle normal messages containing links
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link))

    # Run the bot in persistent polling mode (much more stable than Webhooks for long computations)
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
