"""
YouTube to YouTube Shorts Automation
Main orchestration script
"""
import argparse
import json
import os
import logging
from datetime import datetime
from modules.scraper import get_channel_videos
from modules.downloader import VideoDownloader
from modules.splitter import VideoSplitter
from modules.editor import VideoEditor
from modules.youtube_uploader import YouTubeUploader

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
        videos = get_channel_videos(channel_url, sort_by='date')  # Sort by date (newest first)
        
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
    
    def download_next_video(self) -> tuple:
        """
        Download the next pending video (LATEST/newest first, not highest views)
        Skips already completed videos
        """
        # Find all videos that are NOT completed
        pending = [
            (vid, data) for vid, data in self.tracking['videos'].items()
            if data.get('status') != 'completed'
        ]
        
        if not pending:
            logger.info("No pending videos to download - all videos completed!")
            return None, None
        
        # Videos are already sorted by date (newest first) from scraper
        # Just take the first pending one
        video_id, video_data = pending[0]
        
        logger.info(f"📥 Downloading LATEST video: {video_data['title']}")
        logger.info(f"   Published: {video_data.get('published', 'Unknown')}")
        logger.info(f"   Views: {video_data['views']:,}")
        logger.info(f"   Status: {video_data.get('status', 'pending')}")
        
        # Download with Hindi audio preference
        video_path = self.downloader.download_video(
            video_data['url'], 
            video_id,
            prefer_hindi=True
        )
        
        if video_path:
            self.tracking['videos'][video_id]['status'] = 'downloaded'
            self.tracking['videos'][video_id]['downloaded_at'] = datetime.now().isoformat()
            self._save_tracking()
            return video_id, video_path
        
        return None, None
    
    def process_video(self, video_id: str, video_path: str) -> list:
        """Split and edit video"""
        logger.info(f"Processing video: {video_id}")
        
        video_data = self.tracking['videos'][video_id]
        title = video_data['title']
        
        # Split into segments
        segment_duration = self.config['video_settings']['segment_duration_seconds']
        max_segments = self.config['video_settings']['max_segments_per_video']
        
        segments = self.splitter.split_video(video_path, video_id, segment_duration)
        
        # Limit segments
        if len(segments) > max_segments:
            logger.warning(f"Video has {len(segments)} segments, limiting to {max_segments}")
            segments = segments[:max_segments]
        
        # Add overlays to each segment
        edited_segments = []
        for i, segment_path in enumerate(segments, 1):
            edited_path = self.editor.add_overlays(segment_path, i, title)
            if edited_path:
                edited_segments.append((edited_path, i, title))
        
        logger.info(f"✓ Processed {len(edited_segments)} segments")
        
        # Update tracking
        self.tracking['videos'][video_id]['status'] = 'processed'
        self.tracking['videos'][video_id]['total_parts'] = len(edited_segments)
        self._save_tracking()
        
        return edited_segments
    
    def upload_segments(self, video_id: str, segments: list):
        """Upload segments to YouTube Shorts"""
        logger.info(f"Uploading {len(segments)} segments to YouTube Shorts...")
        
        video_data = self.tracking['videos'][video_id]
        upload_config = self.config['youtube_upload']
        
        # Prepare video info
        videos_to_upload = []
        for video_path, part_num, title in segments:
            # Generate title
            upload_title = upload_config['title_template'].format(
                title=title,
                part=part_num
            )
            
            # Generate description
            upload_description = upload_config['description_template'].format(
                title=title,
                part=part_num,
                total=len(segments),
                url=video_data['url']
            )
            
            videos_to_upload.append({
                'path': video_path,
                'title': upload_title,
                'description': upload_description,
                'part_num': part_num
            })
        
        # Upload
        uploaded_ids = []
        failed = []
        
        for i, video_info in enumerate(videos_to_upload):
            try:
                yt_video_id = self.uploader.upload_short(
                    video_path=video_info['path'],
                    title=video_info['title'],
                    description=video_info['description'],
                    tags=upload_config['tags'],
                    category_id=upload_config['category_id'],
                    privacy_status=upload_config['privacy_status']
                )
                
                if yt_video_id:
                    uploaded_ids.append(yt_video_id)
                    logger.info(f"✓ Part {video_info['part_num']} uploaded successfully")
                else:
                    failed.append(video_info['part_num'])
                    logger.error(f"✗ Part {video_info['part_num']} upload failed")
                
                # Delay between uploads
                if i < len(videos_to_upload) - 1:
                    import time
                    delay = upload_config.get('delay_between_uploads_seconds', 10)
                    logger.info(f"Waiting {delay}s before next upload...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error uploading part {video_info['part_num']}: {e}")
                failed.append(video_info['part_num'])
        
        # Update tracking
        video_data['youtube_video_ids'] = uploaded_ids
        video_data['parts_uploaded'] = [i for i in range(1, len(uploaded_ids) + 1)]
        video_data['last_upload'] = datetime.now().isoformat()
        
        if len(failed) == 0:
            video_data['status'] = 'completed'
        else:
            video_data['status'] = 'partial'
        
        self._save_tracking()
        
        logger.info(f"\n=== Upload Summary ===")
        logger.info(f"Successful: {len(uploaded_ids)}")
        logger.info(f"Failed: {len(failed)}")
        
        return {
            'successful': uploaded_ids,
            'failed': failed
        }
    
    def run_full_automation(self):
        """Run complete automation pipeline"""
        logger.info("=== Starting Full Automation ===")
        
        # 1. Scrape channel
        self.scrape_channel()
        
        # 2. Download next video
        video_id, video_path = self.download_next_video()
        if not video_path:
            logger.warning("No video to process")
            return
        
        # 3. Process video (split + edit)
        segments = self.process_video(video_id, video_path)
        
        # 4. Upload to YouTube
        results = self.upload_segments(video_id, segments)
        
        logger.info("=== Automation Complete ===")
        logger.info(f"Uploaded {len(results['successful'])} YouTube Shorts successfully")
    
    def show_status(self):
        """Show current tracking status"""
        print("\n=== Status Report ===")
        print(f"Channel: {self.tracking['channel_url']}")
        print(f"Last Scrape: {self.tracking.get('last_scrape', 'Never')}")
        print(f"\nTotal Videos: {len(self.tracking['videos'])}")
        
        # Count by status
        status_counts = {}
        for video_data in self.tracking['videos'].values():
            status = video_data.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nStatus Breakdown:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Show top 5 pending
        pending = [
            (vid, data) for vid, data in self.tracking['videos'].items()
            if data.get('status') == 'pending'
        ]
        pending.sort(key=lambda x: x[1]['views'], reverse=True)
        
        if pending:
            print("\nTop 5 Pending Videos (by views):")
            for i, (vid, data) in enumerate(pending[:5], 1):
                print(f"  {i}. {data['title']}")
                print(f"     Views: {data['views']:,} | Duration: {data.get('duration', 'N/A')}")
        
        # Show recently uploaded
        completed = [
            (vid, data) for vid, data in self.tracking['videos'].items()
            if data.get('status') == 'completed'
        ]
        if completed:
            completed.sort(key=lambda x: x[1].get('last_upload', ''), reverse=True)
            print("\n✅ Recently Uploaded (Last 5):")
            for i, (vid, data) in enumerate(completed[:5], 1):
                print(f"  {i}. {data['title']}")
                print(f"     Parts: {len(data.get('youtube_video_ids', []))} | Uploaded: {data.get('last_upload', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description='YouTube to YouTube Shorts Automation')
    parser.add_argument('--channel', help='YouTube channel URL to scrape')
    parser.add_argument('--scrape', action='store_true', help='Only scrape channel')
    parser.add_argument('--download', help='Download specific video by ID')
    parser.add_argument('--process', help='Process (split + edit) specific video by ID')
    parser.add_argument('--upload', action='store_true', help='Upload pending segments')
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
    
    elif args.download:
        video_data = automation.tracking['videos'].get(args.download)
        if video_data:
            automation.downloader.download_video(video_data['url'], args.download)
        else:
            logger.error(f"Video ID not found: {args.download}")
    
    elif args.process:
        video_path = f"downloads/{args.process}.mp4"
        if os.path.exists(video_path):
            automation.process_video(args.process, video_path)
        else:
            logger.error(f"Video file not found: {video_path}")
    
    elif args.upload:
        # Upload all processed but not uploaded segments
        for video_id, video_data in automation.tracking['videos'].items():
            if video_data.get('status') == 'processed':
                # Find edited segments
                processed_dir = automation.config['paths']['processed']
                segments = []
                for i in range(1, video_data.get('total_parts', 0) + 1):
                    seg_path = os.path.join(processed_dir, f"{video_id}_part{i}_edited.mp4")
                    if os.path.exists(seg_path):
                        segments.append((seg_path, i, video_data['title']))
                
                if segments:
                    automation.upload_segments(video_id, segments)
    
    elif args.full:
        automation.run_full_automation()
    
    else:
        # Default: show status
        automation.show_status()


if __name__ == "__main__":
    main()
