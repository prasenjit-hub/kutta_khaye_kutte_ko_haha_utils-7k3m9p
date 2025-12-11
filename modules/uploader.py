"""
Instagram Uploader
Uploads videos to Instagram Reels using instagrapi
"""
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstagramUploader:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.client = Client()
        self.session_file = "instagram_session.json"
        self.last_upload_time = None
    
    def login(self) -> bool:
        """
        Login to Instagram with session caching
        """
        try:
            # Try to load existing session
            if os.path.exists(self.session_file):
                logger.info("Loading existing session...")
                self.client.load_settings(self.session_file)
                self.client.login(self.username, self.password)
                
                try:
                    self.client.get_timeline_feed()
                    logger.info("✓ Session valid, logged in successfully")
                    return True
                except LoginRequired:
                    logger.info("Session expired, logging in again...")
            
            # Fresh login
            logger.info(f"Logging in as {self.username}...")
            self.client.login(self.username, self.password)
            
            # Save session
            self.client.dump_settings(self.session_file)
            logger.info("✓ Logged in successfully and saved session")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def upload_reel(self, video_path: str, caption: str, delay_minutes: int = 0) -> bool:
        """
        Upload video as Instagram Reel
        
        Args:
            video_path: Path to video file
            caption: Caption for the reel
            delay_minutes: Optional delay before upload (for rate limiting)
        
        Returns:
            True if upload successful, False otherwise
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False
        
        # Rate limiting - wait if needed
        if delay_minutes > 0 and self.last_upload_time:
            time_since_last = datetime.now() - self.last_upload_time
            wait_time = timedelta(minutes=delay_minutes) - time_since_last
            
            if wait_time.total_seconds() > 0:
                logger.info(f"Waiting {wait_time.total_seconds():.0f}s before next upload...")
                time.sleep(wait_time.total_seconds())
        
        try:
            logger.info(f"Uploading reel: {video_path}")
            logger.info(f"Caption: {caption}")
            
            # Upload as clip (Reel)
            media = self.client.clip_upload(
                video_path,
                caption=caption
            )
            
            self.last_upload_time = datetime.now()
            logger.info(f"✓ Reel uploaded successfully! Media ID: {media.pk}")
            logger.info(f"  URL: https://www.instagram.com/reel/{media.code}/")
            
            return True
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def upload_multiple(self, video_files: list, caption_template: str, delay_minutes: int = 30) -> dict:
        """
        Upload multiple reels with delay between uploads
        
        Args:
            video_files: List of (video_path, part_num, title) tuples
            caption_template: Template for caption with {title} and {part_text} placeholders
            delay_minutes: Delay between uploads
        
        Returns:
            Dictionary with upload results
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        for i, (video_path, part_num, title) in enumerate(video_files):
            # Generate caption
            caption = caption_template.format(
                title=title,
                part_text=f"Part {part_num}"
            )
            
            # Add delay after first upload
            delay = delay_minutes if i > 0 else 0
            
            success = self.upload_reel(video_path, caption, delay_minutes=delay)
            
            if success:
                results['successful'].append(video_path)
            else:
                results['failed'].append(video_path)
        
        logger.info(f"\n=== Upload Summary ===")
        logger.info(f"Successful: {len(results['successful'])}")
        logger.info(f"Failed: {len(results['failed'])}")
        
        return results


if __name__ == "__main__":
    # Test uploader (requires valid credentials)
    print("⚠️  This is a test mode - please use with caution")
    print("Make sure you have valid credentials in config.json")
    
    import json
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        username = config['instagram']['username']
        password = config['instagram']['password']
        
        if username == "YOUR_INSTAGRAM_USERNAME":
            print("\n✗ Please update config.json with your Instagram credentials first!")
        else:
            uploader = InstagramUploader(username, password)
            
            if uploader.login():
                print("\n✓ Login test successful!")
                print("Ready to upload reels.")
            else:
                print("\n✗ Login test failed")
    
    except FileNotFoundError:
        print("\n✗ config.json not found")
