import os
import random
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip

def get_video_duration(video_path: str) -> float:
    try:
        with VideoFileClip(video_path) as clip:
            return clip.duration
    except Exception as e:
        print(f"Error reading video duration for {video_path}: {e}")
        return 60.0

def get_audio_duration(audio_path: str) -> float:
    try:
        with AudioFileClip(audio_path) as clip:
            return clip.duration
    except Exception as e:
        print(f"Error reading audio duration for {audio_path}: {e}")
        return 60.0

def create_inspirational_video(
    source_video_path: str,
    output_path: str,
    quote: str,
    music_path: str = None,
    target_duration: int = 10
):
    """
    Renders a 10s video clip, mixed with random background music and a centered text overlay.
    """
    try:
        print(f"Rendering: {output_path} with quote: {quote}")
        
        # 1. Load Source Video & Select Random 10s Window
        video_clip = VideoFileClip(source_video_path)
        max_video_start = max(0, video_clip.duration - target_duration)
        video_start = random.uniform(0, max_video_start)
        video_subclip = video_clip.subclip(video_start, video_start + target_duration)
        
        # Crop to portrait aspect ratio (9:16 approx 1080x1920) if it's landscape
        # We assume standard TikTok/Reels proportions
        w, h = video_subclip.size
        target_ratio = 9/16
        current_ratio = w/h
        
        if current_ratio > target_ratio:
            # Video is too wide, crop sides
            new_w = h * target_ratio
            x_center = w / 2
            video_subclip = video_subclip.crop(x1=x_center - new_w/2, y1=0, x2=x_center + new_w/2, y2=h)
        else:
            # Video is too tall, crop top/bottom
            new_h = w / target_ratio
            y_center = h / 2
            video_subclip = video_subclip.crop(x1=0, y1=y_center - new_h/2, x2=w, y2=y_center + new_h/2)
            
        video_subclip = video_subclip.resize(height=1920, width=1080) # Normalize to 1080p vertical
        video_subclip = video_subclip.without_audio() # Mute original audio
        
        # 2. Add Text Overlay
        # Using a standard font that usually exists on Debian/Ubuntu, or fallbacks.
        # ImageMagick will render this.
        text_clip = TextClip(
            txt=quote,
            fontsize=90,
            color='white',
            font='Arial-Bold',
            method='caption', # allows text wrapping
            size=(900, None), # Wrap text if wider than 900px
            align='center',
            stroke_color='black',
            stroke_width=2
        ).set_position('center').set_duration(target_duration)
        
        # 3. Add Music
        final_audio = None
        if music_path and os.path.exists(music_path):
            audio_clip = AudioFileClip(music_path)
            max_audio_start = max(0, audio_clip.duration - target_duration)
            audio_start = random.uniform(0, max_audio_start)
            audio_subclip = audio_clip.subclip(audio_start, audio_start + target_duration)
            
            # Apply fade in/out to avoid harsh cuts
            audio_subclip = audio_subclip.audio_fadein(1.0).audio_fadeout(1.0)
            final_audio = audio_subclip
            
        # 4. Composite & Export
        final_video = CompositeVideoClip([video_subclip, text_clip])
        if final_audio:
            final_video = final_video.set_audio(final_audio)
            
        # Write to file (h264 for mobile compatibility)
        # fps=30 for speed & size, threads=4 to compile multi-core in Docker
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4,
            logger=None # Suppress massive spam logs
        )
        
        # Cleanup memory
        video_clip.close()
        video_subclip.close()
        text_clip.close()
        if final_audio:
            audio_clip.close()
            audio_subclip.close()
        final_video.close()
        
        return output_path
        
    except Exception as e:
        print(f"MoviePy Render Failed: {e}")
        raise e
