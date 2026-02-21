import os
import aiohttp
import asyncio
from google import genai
import time

# --- Configuration ---
GEMINI_API_KEY = os.environ.get("SECRET_GEMINI_API_KEY")
KIE_API_KEY = os.environ.get("SECRET_KIE_API_KEY") # User needs to add this in Railway/Modal

KIE_CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
KIE_STATUS_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"
KIE_FILE_UPLOAD_URL = "https://kieai.redpandaai.co/api/file-stream-upload"

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None
    print("WARNING: GEMINI_API_KEY not set in creative_agent")

async def generate_visual_prompt(quote: str) -> str:
    """
    Given a motivational quote, uses Gemini to generate a highly descriptive,
    cinematic visual prompt for a video generation model.
    """
    if not GEMINI_API_KEY:
        return f"Beautiful cinematic background for the quote: {quote}"

    prompt = (
        f"Actúa como un director de fotografía. Tengo esta frase motivacional: '{quote}'.\n"
        "Escribe un 'prompt' en inglés (máximo 40 palabras) para generar un video de fondo con IA (ej. Luma o Kling). "
        "El video NO debe contener texto. Debe ser cinemático, de alta calidad, realista o estilizado, evocador al sentimiento de la frase. "
        "Solo devuelve el prompt en inglés, sin explicaciones extras."
    )
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error generating prompt: {e}")
        return f"cinematic stunning background video, high quality, masterpiece, nature, 4k"

async def upload_image_to_kie(file_path: str) -> str:
    """
    Uploads a local image to Kie AI's hosting to be used as a reference.
    Returns the hosted URL.
    """
    import aiohttp
    import os
    
    if not KIE_API_KEY:
        raise Exception("KIE_API_KEY is required for image upload")

    headers = {"Authorization": f"Bearer {KIE_API_KEY}"}
    
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=os.path.basename(file_path))
            data.add_field('uploadPath', 'creative-cloner')
            
            async with session.post(KIE_FILE_UPLOAD_URL, headers=headers, data=data) as resp:
                if resp.status != 200:
                    raise Exception(f"Kie upload failed: {resp.status} - {await resp.text()}")
                
                result = await resp.json()
                if result.get("success") or result.get("code") == 200:
                    file_url = result.get("data", {}).get("downloadUrl")
                    if file_url:
                        return file_url
                
                raise Exception(f"Upload failed: {result}")

async def generate_ai_video_kie(prompt: str, image_url: str = None) -> str:
    """
    Calls Kie AI API to generate a video using Kling 3.0.
    Submits task and polls asynchronously until completion.
    Returns the URL of the generated video.
    """
    if not KIE_API_KEY:
        print("WARNING: KIE_API_KEY not set. Returning dummy video URL.")
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "kling-3.0/video",
        "input": {
            "mode": "std",
            "prompt": prompt,
            "duration": "5",
            "multi_shots": False,
            "sound": True,
        }
    }
    
    if image_url:
        payload["input"]["image_urls"] = [image_url]
    else:
        payload["input"]["aspect_ratio"] = "9:16"

    async with aiohttp.ClientSession() as session:
        # 1. Submit the task
        async with session.post(KIE_CREATE_URL, headers=headers, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"Kie API error: {resp.status} - {await resp.text()}")
            result = await resp.json()
            if result.get("code") != 200:
                raise Exception(f"Kie error: {result.get('msg')}")
            
            task_id = result.get("data", {}).get("taskId")
            if not task_id:
                raise Exception(f"No taskId received: {result}")

        # 2. Poll for results
        start_time = time.time()
        max_wait = 600 # 10 minutes
        poll_interval = 10
        
        while time.time() - start_time < max_wait:
            await asyncio.sleep(poll_interval)
            
            url = f"{KIE_STATUS_URL}?taskId={task_id}"
            async with session.get(url, headers=headers) as status_resp:
                if status_resp.status != 200:
                    continue
                    
                status_data = await status_resp.json()
                if status_data.get("code") != 200:
                    continue
                    
                data = status_data.get("data", {})
                state = data.get("state", "unknown")
                
                if state == "success":
                    import json
                    result_json_str = data.get("resultJson", "{}")
                    result_json = json.loads(result_json_str)
                    result_urls = result_json.get("resultUrls", [])
                    if result_urls:
                        return result_urls[0]
                    raise Exception("No result URLs in completed task")
                elif state == "fail":
                    fail_msg = data.get("failMsg", "Unknown error")
                    raise Exception(f"Video generation failed: {fail_msg}")
                    
        raise Exception("Timeout waiting for video generation")

async def process_hybrid_creative_flow(chat_id: int, keyword: str, send_msg_func, send_vid_func, render_remotion_func, vol_path: str, bot_url: str, music_dir: str, image_path: str = None):
    """
    Hybrid Creative Engine:
    1. Generates 1 quote.
    2. Uploads image to Kie (if provided).
    3. Generates 1 visual prompt.
    4. Calls Video API 1 time.
    5. Gathers 1 song.
    6. Renders Remotion video.
    7. Sends to Telegram.
    """
    import aiohttp
    import time
    import os
    import glob
    import random
    
    num_videos = 1 # Reducido a 1 para hacer pruebas más baratas y rápidas
    
    send_msg_func(chat_id, f"🚀 [Motor Creativo] Iniciando generación IA para '{keyword}'...\\n1. Creando frase inspiradora...")
    
    try:
        # Step 1: Generate Quotes
        quote_prompt = f"Genera {num_videos} frase inspiradora corta (máximo 15 palabras) en español sobre el tema: '{keyword}'. Devuélvela sola, sin comillas."
        quote_resp = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=quote_prompt,
        )
        quotes = [line.strip().lstrip('- ').lstrip('1. ') for line in quote_resp.text.split('\\n') if line.strip()][:num_videos]
        
        # Fallback if Gemini fails
        while len(quotes) < num_videos:
            quotes.append(f"La inspiración nace en {keyword}.")
            
        send_msg_func(chat_id, "2. Procesando imagen y creando prompt visual cinemático...")
        
        # Step 1.5: Upload Image if provided
        hosted_image_url = None
        if image_path:
            hosted_image_url = await upload_image_to_kie(image_path)
            print(f"Uploaded reference image to: {hosted_image_url}")
        
        # Step 2: Generate Visual Prompts
        prompt_tasks = [generate_visual_prompt(q) for q in quotes]
        visual_prompts = await asyncio.gather(*prompt_tasks)
        
        send_msg_func(chat_id, f"3. ¡Enviando solicitud a Kling 3.0! (Esto tomará entre 3 y 8 minutos)...")
        
        # Step 3: Generate Videos
        video_tasks = [generate_ai_video_kie(vp, image_url=hosted_image_url) for vp in visual_prompts]
        bg_video_urls = await asyncio.gather(*video_tasks)
        
        send_msg_func(chat_id, "✅ Video de fondo generado. Preparando música y descargando...")
        
        # Step 4: Download Background Videos locally
        timestamp = int(time.time())
        bg_video_paths = []
        
        async with aiohttp.ClientSession() as session:
            for i, bg_url in enumerate(bg_video_urls):
                path = os.path.join(vol_path, f"bg_{chat_id}_{timestamp}_{i}.mp4")
                async with session.get(bg_url) as resp:
                    if resp.status == 200:
                        with open(path, 'wb') as f:
                            f.write(await resp.read())
                        bg_video_paths.append(path)
                    else:
                        raise Exception(f"Failed to download background video {i}")

        # Step 5: Assign Music
        music_files = []
        for ext in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.flac"):
            music_files.extend(glob.glob(os.path.join(music_dir, ext)))
            
        selected_musics = [None] * num_videos
        if music_files:
            if len(music_files) >= num_videos:
                selected_musics = random.sample(music_files, num_videos)
            else:
                selected_musics = [random.choice(music_files) for _ in range(num_videos)]

        def get_video_duration(path):
            import subprocess
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path]
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return float(result.stdout.strip())
            except:
                return 60.0

        # Step 6: Render in Remotion & Send
        send_msg_func(chat_id, "⚙️ Ensamblando video final en Remotion...")
        
        loop = asyncio.get_running_loop()
        
        for i in range(num_videos):
            output_filename = f"creative_out_{chat_id}_{timestamp}_{i+1}.mp4"
            output_path = os.path.join(vol_path, output_filename)
            
            # Prepare Background Video URL
            video_http_url = f"{bot_url}/tmp/{os.path.basename(bg_video_paths[i])}"
            video_start = 0 
            
            # Prepare Music URL & Random Start
            music_path = selected_musics[i]
            music_http_url = ""
            music_start = 0
            if music_path:
                music_dur = get_video_duration(music_path)
                music_start = random.uniform(0, max(0, music_dur - 10))
                music_filename = os.path.basename(music_path)
                music_http_url = f"{bot_url}/music/{music_filename}"
            
            props = {
                "videoUrl": video_http_url,
                "videoStart": video_start,
                "musicUrl": music_http_url,
                "musicStart": music_start,
                "quoteText": quotes[i]
            }
            
            try:
                await loop.run_in_executor(None, render_remotion_func, output_path, props)
                send_vid_func(chat_id, output_path, caption=f"✨ Video IA Completado\\nFrase: {quotes[i]}")
            except Exception as render_err:
                print(f"Render failed for {i+1}: {render_err}")
                send_msg_func(chat_id, f"⚠️ Error ensamblando video {i+1}: {render_err}")

    except Exception as e:
        import traceback
        full_trace = traceback.format_exc()
        print(f"CRITICAL HYBRID ERROR:\n{full_trace}")
        send_msg_func(chat_id, f"❌ Error crítico en Híbrido:\n{str(e)}\n\nTraceback:\n{full_trace[-500:]}")
