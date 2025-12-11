"""
YouTube Video Downloader
Downloads videos in 1080p with audio using yt-dlp
"""
import yt_dlp
import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    def download_video(self, video_url: str, video_id: str, prefer_hindi: bool = True) -> Optional[str]:
        """
        Download video in 1080p with best audio (Hindi preferred if available)
        
        Args:
            video_url: YouTube video URL
            video_id: Video ID for filename
            prefer_hindi: If True, prefer Hindi audio track
        
        Returns:
            Path to downloaded file or None if failed
        """
        output_path = os.path.join(self.download_dir, f"{video_id}.mp4")
        
        # Check if already downloaded
        if os.path.exists(output_path):
            logger.info(f"Video already downloaded: {output_path}")
            return output_path
        
        # Format string with Hindi audio preference
        if prefer_hindi:
            # Try Hindi audio first, fallback to best audio
            format_str = 'bestvideo[height<=1080][ext=mp4]+bestaudio[language=hi]/bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]'
            logger.info("Trying to download with Hindi audio...")
        else:
            format_str = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]'
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'quiet': False,
            'no_warnings': False,
            'logger': logger,
            'progress_hooks': [self._progress_hook],
        }
        
        try:
            logger.info(f"Downloading video: {video_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                
                # Check if Hindi audio was selected
                if prefer_hindi and 'requested_formats' in info:
                    audio_lang = info.get('requested_formats', [{}])[-1].get('language', 'unknown')
                    if audio_lang == 'hi':
                        logger.info("✓ Downloaded with Hindi audio!")
                    else:
                        logger.info(f"Hindi audio not available, using {audio_lang}")
            
            if os.path.exists(output_path):
                logger.info(f"Download complete: {output_path}")
                return output_path
            else:
                logger.error("Download failed - file not found")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def _progress_hook(self, d):
        """Progress callback for download status"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            logger.info(f"Downloading: {percent} at {speed} ETA: {eta}")
        elif d['status'] == 'finished':
            logger.info("Download finished, now merging...")


if __name__ == "__main__":
    # Test downloader
    downloader = VideoDownloader()
    
    # Test with a short video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = downloader.download_video(test_url, "test_video")
    
    if result:
        print(f"\n✓ Downloaded successfully to: {result}")
    else:
        print("\n✗ Download failed")
