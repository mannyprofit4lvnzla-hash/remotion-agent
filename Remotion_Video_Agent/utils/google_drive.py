import gdown
import os
import random

def download_file_from_google_drive(url: str, output_path: str):
    """
    Downloads a file from Google Drive to the specified output path.
    """
    # gdown handles various drive link formats
    gdown.download(url, output_path, quiet=False, fuzzy=True)

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
 
