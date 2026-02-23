import sys
from utils.google_drive import download_file_from_google_drive

url = "https://drive.google.com/file/d/1wb0yH6zKmCAjSZDbmSBOagPz35VCTBK_v/view?usp=drivesdk"
try:
    download_file_from_google_drive(url, "/tmp/test.mp4")
    print("Success")
except Exception as e:
    print(f"Exception caught exactly as: {e}")
