import os
import glob
import random
import asyncio
import subprocess
import shutil
import time
from typing import List

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
from google import genai
from utils.google_drive import download_file_from_google_drive, download_folder_from_google_drive
import creative_agent

# --- Configuration ---
BOT_TOKEN = os.environ.get("SECRET_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("SECRET_GEMINI_API_KEY")
WEBHOOK_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN") # e.g. https://my-app.up.railway.app
if WEBHOOK_URL and not WEBHOOK_URL.startswith("http"):
    WEBHOOK_URL = f"https://{WEBHOOK_URL}"
    
VOL_PATH = "/tmp" # Working directory for downloads/renders
MUSIC_DIR = os.path.join(VOL_PATH, "music")
if not os.path.exists(MUSIC_DIR):
    os.makedirs(MUSIC_DIR)

app = FastAPI()

# Mount static files to allow Remotion (Chromium) to access them via HTTP
app.mount("/tmp", StaticFiles(directory=VOL_PATH), name="tmp")
app.mount("/music", StaticFiles(directory=MUSIC_DIR), name="music")

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None
    print("WARNING: GEMINI_API_KEY not set")

# --- Helper Functions ---

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"Error sending message: {e}")

def send_telegram_video(chat_id, video_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {'chat_id': chat_id, 'caption': caption}
            print(f"Uploading video {video_path}...")
            r = requests.post(url, data=data, files=files)
            print(f"Upload result: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Error sending video: {e}")

def download_telegram_photo(file_id: str, output_path: str):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]
    
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    img_resp = requests.get(download_url)
    img_resp.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(img_resp.content)

async def generate_quotes(keyword: str, count: int = 3) -> List[str]:
    # Simple direct generation
    prompt = f"Genera {count} frases inspiradoras cortas (máximo 15 palabras) en español sobre el tema: '{keyword}'. Devuélvelas en formato de lista plana, una por línea."
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text
        # Clean up list format
        lines = [line.strip().lstrip('- ').lstrip('1. ') for line in text.split('\\n') if line.strip()]
        return lines[:count]
    except Exception as e:
        print(f"Gemini error: {e}")
        return [f"Inspírate con {keyword}"] * count

def get_video_duration(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 60.0 # Fallback

async def render_remotion_video(output_path, props):
    # npx remotion render src/index.ts MyComposition out/video.mp4 --props='{...}'
    # We are in /app, remotion is in /app/remotion
    # cmd needs to run inside /app/remotion or point to it
    
    import json
    import asyncio
    props_json = json.dumps(props)
    
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        "MyComposition",
        output_path,
        f"--props={props_json}",
        "--chromium-disable-web-security",
        "--chromium-ignore-certificate-errors",
        "--chromium-disable-audio-output",
        "--disable-features=AudioServiceOutOfProcess",
        "--chromium-disable-software-rasterizer",
        "--log=verbose"
    ]
    
    # Check for specific browser executable (e.g., in Docker)
    browser_executable = "/usr/bin/chromium-wrapper"
    if os.path.exists(browser_executable):
        cmd.append(f"--browser-executable={browser_executable}")
    
    print(f"Executing Remotion: {' '.join(cmd)}")
    
    def run_subproc():
        return subprocess.run(
            cmd,
            cwd=os.path.join(os.getcwd(), "remotion"), # Run inside remotion dir
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_subproc)
    
    if result.returncode != 0:
        full_error = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        print(f"Remotion Error Details:\n{full_error}")
        # Return last 1000 chars to Telegram to capture more context
        raise Exception(f"Remotion failed: {result.stderr[-1000:]}")
    
    print("Remotion render success!")
    return output_path

# --- Main Logic ---

async def import_music_flow(chat_id: int, url: str):
    send_telegram_message(chat_id, "🎵 Iniciando importación de música (esto puede tardar)...")
    try:
        download_folder_from_google_drive(url, MUSIC_DIR)
        count = len(glob.glob(os.path.join(MUSIC_DIR, "*")))
        send_telegram_message(chat_id, f"✅ Importación completada. Ahora tienes {count} canciones.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error importando música: {e}")

async def process_video_flow(chat_id: int, drive_url: str, keyword: str):
    send_telegram_message(chat_id, f"🚀 Iniciando proceso para '{keyword}'...\\n1. Descargando video fuente...")
    
    # 1. Download Source Video
    timestamp = int(time.time())
    source_video_path = os.path.join(VOL_PATH, f"source_{chat_id}_{timestamp}.mp4")
    
    try:
        download_file_from_google_drive(drive_url, source_video_path)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error descargando video: {str(e)}")
        return

    source_duration = get_video_duration(source_video_path)
    print(f"Source video duration: {source_duration}s")
    
    # 2. Generate content
    send_telegram_message(chat_id, "2. Generando frases y seleccionando música...")
    quotes = await generate_quotes(keyword, count=3)
    
    music_files = []
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.flac"):
        music_files.extend(glob.glob(os.path.join(MUSIC_DIR, ext)))
        
    if not music_files:
        print("No music files found! Please add audio files to music/ directory.")
        send_telegram_message(chat_id, "⚠️ No hay música en la librería. Usando modo silencio.")
        # Create dummy music list to prevent crash
        selected_musics = [None] * 3
    else:
        # Select 3 unique songs (or repeat if <3)
        if len(music_files) >= 3:
            selected_musics = random.sample(music_files, 3)
        else:
            selected_musics = [random.choice(music_files) for _ in range(3)]

        # 3. Render Loop
    send_telegram_message(chat_id, "3. Renderizando 3 videos (esto tomará un momento)...")
    
    for i in range(3):
        quote = quotes[i] if i < len(quotes) else quotes[0]
        music_path = selected_musics[i]
        
        # Calculate random starts
        # Video: Random start between 0 and (Duration - 10s)
        max_video_start = max(0, source_duration - 10)
        video_start = random.uniform(0, max_video_start)
        
        # Music: Random start
        music_start = 0
        if music_path:
            music_dur = get_video_duration(music_path)
            music_start = random.uniform(0, max(0, music_dur - 10))
            music_path = os.path.abspath(music_path)
        
        # We don't need to copy to remotion_public_dir anymore! 
        # We can serve it directly from the FastAPI mounted static files:
        # /tmp -> VOL_PATH
        # /music -> MUSIC_DIR
        output_filename = f"output_{chat_id}_{timestamp}_{i+1}.mp4"
        output_path = os.path.join(VOL_PATH, output_filename)
        
        port = int(os.environ.get("PORT", 8000))
        local_base_url = f"http://127.0.0.1:{port}"
        
        video_filename = os.path.basename(source_video_path)
        video_local_url = f"{local_base_url}/tmp/{video_filename}"
        
        music_local_url = ""
        if music_path:
            music_filename = os.path.basename(music_path)
            music_local_url = f"{local_base_url}/music/{music_filename}"
        
        props = {
            "videoUrl": video_local_url,
            "videoStart": video_start,
            "musicUrl": music_local_url,
            "musicStart": music_start,
            "quoteText": quote
        }
        
        try:
            print(f"Rendering video {i+1}...")
            await render_remotion_video(output_path, props)
            
            # Send result
            send_telegram_video(chat_id, output_path, caption=f"✨ Opción {i+1}\\nFrase: {quote}")
            
        except Exception as e:
            print(f"Render failed for {i+1}: {e}")
            send_telegram_message(chat_id, f"⚠️ Error renderizando video {i+1}: {e}")

    send_telegram_message(chat_id, "✅ ¡Proceso completado!")

# --- Webhook ---

@app.post("/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    photos = message.get("photo")
    
    if not chat_id:
        return JSONResponse({"status": "ignored"})
        
    if photos:
        # Photo received. Start Image-to-Video Engine.
        best_photo = photos[-1]
        file_id = best_photo["file_id"]
        caption = message.get("caption", "Motivación")
        
        timestamp = int(time.time())
        image_path = os.path.join(VOL_PATH, f"photo_{chat_id}_{timestamp}.jpg")
        
        try:
            download_telegram_photo(file_id, image_path)
            
            background_tasks.add_task(
                creative_agent.process_hybrid_creative_flow,
                chat_id=chat_id,
                keyword=caption,
                send_msg_func=send_telegram_message,
                send_vid_func=send_telegram_video,
                render_remotion_func=render_remotion_video,
                vol_path=VOL_PATH,
                music_dir=MUSIC_DIR,
                image_path=image_path
            )
            return JSONResponse({"status": "creative_engine_photo_processing"})
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Error descargando foto: {e}")
            return JSONResponse({"status": "photo_error"})
    
    if not text:
        return JSONResponse({"status": "ignored"})
        
    parts = text.split(maxsplit=1)
    command = parts[0]
    
    if command == "/start" or command == "/help":
        welcome_msg = (
            "👋 **¡Hola! Soy tu Bot de Inspiración (Remotion v1)**\\n\\n"
            "🎵 **Primero:** Importa tu música enviando:\\n"
            "`/importmusic https://drive.google.com/drive/folders/...`\\n\\n"
            "🎥 **Luego:** Crea videos desde Google Drive:\\n"
            "`https://drive.google.com/file/d/... Motivación`\\n\\n"
            "✨ **NUEVO (Creative Engine):** Genera un video completamente con IA enviando:\\n"
            "`/create_ai_video Tu frase motivacional aquí`"
        )
        send_telegram_message(chat_id, welcome_msg)
        return JSONResponse({"status": "welcome_sent"})

    if command == "/create_ai_video" and len(parts) > 1:
        quote = parts[1]
        
        background_tasks.add_task(
            creative_agent.process_hybrid_creative_flow,
            chat_id=chat_id,
            keyword=quote,
            send_msg_func=send_telegram_message,
            send_vid_func=send_telegram_video,
            render_remotion_func=render_remotion_video,
            vol_path=VOL_PATH,
            music_dir=MUSIC_DIR
        )
        return JSONResponse({"status": "creative_engine_processing"})

    if command == "/importmusic" and len(parts) > 1:
        url = parts[1]
        background_tasks.add_task(import_music_flow, chat_id, url)
        return JSONResponse({"status": "importing"})
        
    url = parts[0]
    keyword = parts[1] if len(parts) > 1 else "Inspiración"
    
    if "drive.google.com" in url or "youtube.com" in url: # Add regex validation if needed
        background_tasks.add_task(process_video_flow, chat_id, url, keyword)
        return JSONResponse({"status": "processing"})
    else:
        return JSONResponse({"status": "ignored", "reason": "not a link"})

@app.post("/importmusic")
async def import_music_endpoint(request: Request, background_tasks: BackgroundTasks):
    pass 
    
@app.get("/health")
def health():
    return {"status": "ok", "engine": "remotion"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
