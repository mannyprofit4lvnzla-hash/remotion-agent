import gdown
import os
import random

def download_file_from_google_drive(url: str, output_path: str):
    """
    Downloads a file from Google Drive to the specified output path.
    Tries gdown first. If it fails due to permissions/limits, falls back to yt-dlp.
    """
    try:
        # gdown handles various drive link formats
        gdown.download(url, output_path, quiet=False, fuzzy=True)
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("gdown created an empty file or failed to create file")
    except Exception as e:
        print(f"gdown failed with error: {e}. Trying yt-dlp fallback...")
        import subprocess
        # yt-dlp is extremely robust against Google rate limits and permission bugs
        cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4", "-o", output_path, url]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"yt-dlp fallback failed: {result.stderr}")

def download_folder_from_google_drive(url: str, output_dir: str):
    """
    Downloads a folder from Google Drive to the specified output directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Downloading folder from {url} to {output_dir}")
    
    gdown_failed = False
    try:
        gdown.download_folder(url, output=output_dir, quiet=False, use_cookies=False)
        if len(os.listdir(output_dir)) == 0:
            print("gdown returned correctly but 0 files were downloaded. Triggering fallback.")
            gdown_failed = True
    except Exception as e:
        print(f"gdown folder download exception: {e}")
        gdown_failed = True
        
    if gdown_failed:
        print("Falling back to yt-dlp for Google Drive folder scraping...")
        import subprocess
        # yt-dlp natively supports Google Drive folders. We force audio extraction.
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--yes-playlist",
            "-o", f"{output_dir}/%(title)s.%(ext)s",
            url
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"yt-dlp stdout: {result.stdout}")
            print(f"yt-dlp stderr: {result.stderr}")
            raise Exception(f"Both gdown and yt-dlp failed to download the folder. yt-dlp error: {result.stderr}")
 
