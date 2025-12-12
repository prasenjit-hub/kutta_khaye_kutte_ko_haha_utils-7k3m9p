"""
YouTube to YouTube Shorts Automation
Main orchestration script - OPTIMIZED for incremental processing

Key Features:
- Only processes segments that need to be uploaded (not all)
- Resumes from where it left off
- Max 3 uploads per run
- Tracks progress in tracking.json
"""
import argparse
import json
import os
import logging
import shutil
from datetime import datetime
from modules.scraper import get_channel_videos
from modules.downloader import VideoDownloader
from modules.splitter import VideoSplitter
from modules.editor import VideoEditor
from modules.youtube_uploader import YouTubeUploader

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class YouTubeShortsAutomation:
    def __init__(self, config_path: str = 'config.json', tracking_path: str = 'tracking.json'):
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.tracking_path = tracking_path
        self.tracking = self._load_tracking()
        
        # Create directories
        for path in self.config['paths'].values():
            os.makedirs(path, exist_ok=True)
        
        # Initialize modules
        self.downloader = VideoDownloader(self.config['paths']['downloads'])
        self.splitter = VideoSplitter(self.config['paths']['processed'])
        self.editor = VideoEditor(self.config)
        
        # YouTube uploader (lazy init)
        self._uploader = None
        
        # Get limits from config
        self.max_uploads_per_run = self.config['video_settings'].get('max_uploads_per_run', 3)
        self.max_segments_per_video = self.config['video_settings'].get('max_segments_per_video', 10)
        self.segment_duration = self.config['video_settings'].get('segment_duration_seconds', 60)
    
    @property
    def uploader(self):
        """Lazy initialize uploader to avoid authentication on every run"""
        if self._uploader is None:
            credentials_file = self.config['youtube_upload']['credentials_file']
            self._uploader = YouTubeUploader(credentials_file)
        return self._uploader
    
    def _load_tracking(self) -> dict:
        """Load tracking database"""
        if os.path.exists(self.tracking_path):
            with open(self.tracking_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'channel_url': '', 'last_scrape': None, 'videos': {}}
    
    def _save_tracking(self):
        """Save tracking database"""
        with open(self.tracking_path, 'w', encoding='utf-8') as f:
            json.dump(self.tracking, f, indent=2, ensure_ascii=False)
    
    def scrape_channel(self, channel_url: str = None):
        """Scrape YouTube channel and update tracking (sorted by date - newest first)"""
        if channel_url is None:
            channel_url = self.config['youtube_channel']
        
        logger.info(f"Scraping channel: {channel_url}")
        videos = get_channel_videos(channel_url, sort_by='date')
        
        # Update tracking
        self.tracking['channel_url'] = channel_url
        self.tracking['last_scrape'] = datetime.now().isoformat()
        
        for video in videos:
            video_id = video['id']
            if video_id not in self.tracking['videos']:
                self.tracking['videos'][video_id] = {
                    'title': video['title'],
                    'views': video['views'],
                    'duration': video['duration'],
                    'published': video.get('published', 'Unknown'),
                    'url': video['url'],
                    'status': 'pending',
                    'parts_uploaded': [],
                    'total_parts': 0,
                    'youtube_video_ids': [],
                    'downloaded_at': None,
                    'last_upload': None
                }
            else:
                # Update views and published date
                self.tracking['videos'][video_id]['views'] = video['views']
                self.tracking['videos'][video_id]['published'] = video.get('published', 'Unknown')
        
        self._save_tracking()
        logger.info(f"✓ Scraped {len(videos)} videos (sorted by date - newest first)")
        return videos
    
    def get_next_video_to_process(self) -> tuple:
        """
        Get the next video that needs processing.
        Priority: partial (resume) > pending (new)
        Returns: (video_id, video_data) or (None, None)
        """
        # First, look for partial videos (resume upload)
        for video_id, data in self.tracking['videos'].items():
            if data.get('status') == 'partial':
                logger.info(f"📌 Resuming partial video: {data['title']}")
                return video_id, data
        
        # Then, look for pending videos (new)
        for video_id, data in self.tracking['videos'].items():
            if data.get('status') == 'pending':
                logger.info(f"📌 Starting new video: {data['title']}")
                return video_id, data
        
        logger.info("✅ All videos completed!")
        return None, None
    
    def run_full_automation(self):
        """
        Run complete automation pipeline - OPTIMIZED
        
        Key optimizations:
        1. Only create segments we need (not all)
        2. Only edit segments we need
        3. Max 3 uploads per run
        4. Resume from last uploaded part
        """
        logger.info("=" * 60)
        logger.info("=== Starting Full Automation (Optimized) ===")
        logger.info("=" * 60)
        
        # 1. Scrape channel for latest videos
        self.scrape_channel()
        
        # 2. Find next video to process
        video_id, video_data = self.get_next_video_to_process()
        if not video_id:
            logger.info("No videos to process!")
            return
        
        logger.info(f"\n📹 Processing: {video_data['title']}")
        logger.info(f"   Status: {video_data.get('status')}")
        logger.info(f"   Parts uploaded: {video_data.get('parts_uploaded', [])}")
        
        # 3. Download video (if not already downloaded)
        video_path = os.path.join(self.config['paths']['downloads'], f"{video_id}.mp4")
        
        if not os.path.exists(video_path):
            logger.info(f"\n📥 Downloading video...")
            video_path = self.downloader.download_video(
                video_data['url'],
                video_id,
                prefer_hindi=False  # English audio
            )
            if not video_path:
                logger.error("Download failed!")
                return
        else:
            logger.info(f"✓ Video already downloaded: {video_path}")
        
        # 4. Calculate which parts to process
        parts_already_uploaded = video_data.get('parts_uploaded', [])
        next_part_to_upload = max(parts_already_uploaded) + 1 if parts_already_uploaded else 1
        
        # Calculate total parts for this video
        from modules.splitter import get_video_duration
        total_duration = get_video_duration(video_path)
        total_possible_parts = int(total_duration / self.segment_duration)
        if total_duration % self.segment_duration >= 10:  # Add 1 if remainder >= 10s
            total_possible_parts += 1
        
        # Limit to max_segments_per_video
        total_parts = min(total_possible_parts, self.max_segments_per_video)
        
        logger.info(f"\n📊 Video Analysis:")
        logger.info(f"   Total duration: {total_duration:.2f}s")
        logger.info(f"   Total parts (limited to {self.max_segments_per_video}): {total_parts}")
        logger.info(f"   Parts already uploaded: {parts_already_uploaded}")
        logger.info(f"   Next part to upload: {next_part_to_upload}")
        logger.info(f"   Max uploads this run: {self.max_uploads_per_run}")
        
        # Check if video is already complete
        if next_part_to_upload > total_parts:
            logger.info(f"✅ Video already complete! Moving to next video...")
            self.tracking['videos'][video_id]['status'] = 'completed'
            self._save_tracking()
            # Recursively process next video
            return self.run_full_automation()
        
        # 5. Calculate which parts to process THIS RUN
        parts_to_process = []
        for part_num in range(next_part_to_upload, total_parts + 1):
            if len(parts_to_process) >= self.max_uploads_per_run:
                break
            parts_to_process.append(part_num)
        
        logger.info(f"\n🎯 This run will process parts: {parts_to_process}")
        
        # 6. Create ONLY the segments we need
        logger.info(f"\n✂️ Creating only required segments...")
        processed_dir = self.config['paths']['processed']
        
        segments_to_upload = []
        
        for part_num in parts_to_process:
            # Calculate time range for this segment
            start_time = (part_num - 1) * self.segment_duration
            end_time = min(part_num * self.segment_duration, total_duration)
            
            # Create segment filename
            segment_filename = f"{video_id}_part{part_num}.mp4"
            segment_path = os.path.join(processed_dir, segment_filename)
            edited_filename = f"{video_id}_part{part_num}_edited.mp4"
            edited_path = os.path.join(processed_dir, edited_filename)
            
            # Create segment using FFmpeg
            logger.info(f"\n--- Part {part_num} ---")
            logger.info(f"Creating segment: {start_time:.2f}s - {end_time:.2f}s")
            
            import subprocess
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(end_time - start_time),
                '-c:v', 'libx264',
                '-preset', 'slow',  # Good quality encoding
                '-c:a', 'aac',
                '-b:a', '256k',  # Good audio quality
                '-loglevel', 'error',
                segment_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to create segment {part_num}: {result.stderr}")
                continue
            
            logger.info(f"✓ Segment {part_num} created")
            
            # Edit segment (add overlay, convert to 9:16)
            logger.info(f"Editing segment {part_num}...")
            edited_result = self.editor.add_overlays(
                segment_path, 
                part_num, 
                video_data['title'],
                edited_path
            )
            
            if edited_result:
                logger.info(f"✓ Segment {part_num} edited")
                segments_to_upload.append((edited_path, part_num, video_data['title']))
                
                # Clean up raw segment to save space
                if os.path.exists(segment_path):
                    os.remove(segment_path)
            else:
                logger.error(f"Failed to edit segment {part_num}")
        
        if not segments_to_upload:
            logger.error("No segments to upload!")
            return
        
        # 7. Upload segments
        logger.info(f"\n📤 Uploading {len(segments_to_upload)} segments to YouTube...")
        
        upload_config = self.config['youtube_upload']
        uploaded_parts = list(parts_already_uploaded)  # Copy existing
        uploaded_ids = list(video_data.get('youtube_video_ids', []))
        
        for edited_path, part_num, title in segments_to_upload:
            # Generate title and description
            upload_title = upload_config['title_template'].format(
                title=title,
                part=part_num
            )
            
            # Ensure title doesn't exceed 99 characters (YouTube limit is 100)
            if len(upload_title) > 99:
                # Calculate how much to trim from the original title
                hashtags = " #shorts #viral #mrbeast"
                part_text = f" - Part {part_num}"
                available_chars = 99 - len(hashtags) - len(part_text) - 3  # -3 for "..."
                truncated_title = title[:available_chars] + "..."
                upload_title = f"{truncated_title}{part_text}{hashtags}"
                logger.info(f"Title truncated to {len(upload_title)} chars")
            
            upload_description = upload_config['description_template'].format(
                title=title,
                part=part_num,
                total=total_parts,
                url=video_data['url']
            )
            
            # Upload
            try:
                yt_video_id = self.uploader.upload_short(
                    video_path=edited_path,
                    title=upload_title,
                    description=upload_description,
                    tags=upload_config['tags'],
                    category_id=upload_config['category_id'],
                    privacy_status=upload_config['privacy_status']
                )
                
                if yt_video_id:
                    uploaded_parts.append(part_num)
                    uploaded_ids.append(yt_video_id)
                    logger.info(f"✓ Part {part_num} uploaded: https://youtube.com/shorts/{yt_video_id}")
                else:
                    logger.error(f"✗ Part {part_num} upload failed")
                
                    
            except Exception as e:
                logger.error(f"Error uploading part {part_num}: {e}")
            
            # Clean up edited segment after upload
            if os.path.exists(edited_path):
                os.remove(edited_path)
        
        # 8. Update tracking
        self.tracking['videos'][video_id]['parts_uploaded'] = sorted(uploaded_parts)
        self.tracking['videos'][video_id]['total_parts'] = total_parts
        self.tracking['videos'][video_id]['youtube_video_ids'] = uploaded_ids
        self.tracking['videos'][video_id]['last_upload'] = datetime.now().isoformat()
        
        # Check if video is now complete
        if len(uploaded_parts) >= total_parts:
            self.tracking['videos'][video_id]['status'] = 'completed'
            logger.info(f"\n🎉 Video COMPLETED! All {total_parts} parts uploaded.")
        else:
            self.tracking['videos'][video_id]['status'] = 'partial'
            remaining = total_parts - len(uploaded_parts)
            logger.info(f"\n📊 Progress: {len(uploaded_parts)}/{total_parts} parts uploaded")
            logger.info(f"   Remaining: {remaining} parts")
        
        self._save_tracking()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("=== Automation Complete ===")
        logger.info("=" * 60)
        logger.info(f"Video: {video_data['title']}")
        logger.info(f"Parts uploaded this run: {parts_to_process}")
        logger.info(f"Total parts uploaded: {len(uploaded_parts)}/{total_parts}")
        logger.info(f"Status: {self.tracking['videos'][video_id]['status']}")
    
    def show_status(self):
        """Show current tracking status"""
        print("\n" + "=" * 60)
        print("=== Status Report ===")
        print("=" * 60)
        print(f"Channel: {self.tracking.get('channel_url', 'Not set')}")
        print(f"Last Scrape: {self.tracking.get('last_scrape', 'Never')}")
        print(f"\nTotal Videos: {len(self.tracking.get('videos', {}))}")
        
        # Count by status
        status_counts = {}
        for video_data in self.tracking.get('videos', {}).values():
            status = video_data.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nStatus Breakdown:")
        for status, count in status_counts.items():
            emoji = {'completed': '✅', 'partial': '🔄', 'pending': '⏳'}.get(status, '❓')
            print(f"  {emoji} {status}: {count}")
        
        # Show partial videos (in progress)
        partial = [
            (vid, data) for vid, data in self.tracking.get('videos', {}).items()
            if data.get('status') == 'partial'
        ]
        if partial:
            print("\n🔄 In Progress:")
            for vid, data in partial:
                uploaded = len(data.get('parts_uploaded', []))
                total = data.get('total_parts', '?')
                print(f"  • {data['title']}")
                print(f"    Progress: {uploaded}/{total} parts")
        
        # Show next pending
        pending = [
            (vid, data) for vid, data in self.tracking.get('videos', {}).items()
            if data.get('status') == 'pending'
        ]
        if pending:
            print(f"\n⏳ Next Pending: {pending[0][1]['title']}")


def main():
    parser = argparse.ArgumentParser(description='YouTube to YouTube Shorts Automation')
    parser.add_argument('--channel', help='YouTube channel URL to scrape')
    parser.add_argument('--scrape', action='store_true', help='Only scrape channel')
    parser.add_argument('--status', action='store_true', help='Show tracking status')
    parser.add_argument('--full', action='store_true', help='Run full automation pipeline')
    
    args = parser.parse_args()
    
    # Create automation instance
    automation = YouTubeShortsAutomation()
    
    # Execute requested action
    if args.status:
        automation.show_status()
    elif args.scrape:
        automation.scrape_channel(args.channel)
    elif args.full:
        automation.run_full_automation()
    else:
        # Default: show status
        automation.show_status()


if __name__ == "__main__":
    main()
