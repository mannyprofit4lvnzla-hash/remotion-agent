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
        cmd = ["yt-dlp", "-o", output_path, url]
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
    # gdown download_folder handles public folder links
    # fuzzy=True helps with extracting ID from messy URLs
    gdown.download_folder(url, output=output_dir, quiet=False, use_cookies=False)
 
