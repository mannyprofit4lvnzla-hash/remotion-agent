import sys
try:
    import moviepy.editor
    from google import genai
    import telegram
    import yt_dlp
    import gdown
    print("All heavy dependencies imported cleanly.")
except ImportError as e:
    print(f"Missing dependency: {e}")
