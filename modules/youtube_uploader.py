"""
YouTube Shorts Uploader
Automatic video upload to YouTube using official API
"""
import os
import pickle
import logging
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    def __init__(self, credentials_file='youtube_credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'youtube_token.pickle'
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with YouTube using OAuth 2.0
        First time: Browser open hoga for permission
        Next time: Saved token use karega
        """
        creds = None
        
        # Load saved token if exists
        if os.path.exists(self.token_file):
            logger.info("Loading saved YouTube credentials...")
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing YouTube credentials...")
                creds.refresh(Request())
            else:
                logger.info("First time authentication - browser will open...")
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    logger.error("Please follow setup instructions in YOUTUBE_SETUP.md")
                    raise FileNotFoundError(f"Missing {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("✓ Credentials saved")
        
        # Build YouTube service
        self.youtube = build('youtube', 'v3', credentials=creds)
        logger.info("✓ YouTube API authenticated successfully")
    
    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str = '',
        tags: list = None,
        category_id: str = '22',  # 22 = People & Blogs
        privacy_status: str = 'public'  # public, private, unlisted
    ) -> Optional[str]:
        """
        Upload video to YouTube Shorts
        
        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: public, private, or unlisted
        
        Returns:
            Video ID if successful, None otherwise
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        # Add #Shorts to description for YouTube Shorts
        if '#Shorts' not in description and '#shorts' not in description:
            description = description + '\n\n#Shorts'
        
        if tags is None:
            tags = ['shorts']
        elif 'shorts' not in [t.lower() for t in tags]:
            tags.append('shorts')
        
        # Video metadata
        body = {
            'snippet': {
                'title': title[:100],  # Max 100 chars
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Media file
        media = MediaFileUpload(
            video_path,
            mimetype='video/*',
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )
        
        try:
            logger.info(f"Uploading to YouTube: {title}")
            logger.info(f"File: {video_path}")
            
            # Execute upload
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/shorts/{video_id}"
            
            logger.info(f"✓ Upload successful!")
            logger.info(f"  Video ID: {video_id}")
            logger.info(f"  URL: {video_url}")
            
            return video_id
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None
    
    def upload_batch(
        self,
        videos: list,
        title_template: str = '{title} - Part {part}',
        description_template: str = '{title}\n\n#Shorts #Viral',
        tags: list = None,
        delay_seconds: int = 0
    ) -> dict:
        """
        Upload multiple videos
        
        Args:
            videos: List of (video_path, part_num, title) tuples
            title_template: Template for title
            description_template: Template for description
            tags: Common tags for all videos
            delay_seconds: Delay between uploads
        
        Returns:
            Dictionary with upload results
        """
        import time
        
        results = {
            'successful': [],
            'failed': []
        }
        
        for i, (video_path, part_num, video_title) in enumerate(videos):
            # Generate title and description
            title = title_template.format(title=video_title, part=part_num)
            description = description_template.format(title=video_title, part=part_num)
            
            # Upload
            video_id = self.upload_short(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags
            )
            
            if video_id:
                results['successful'].append({
                    'video_path': video_path,
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/shorts/{video_id}"
                })
            else:
                results['failed'].append(video_path)
            
            # Delay before next upload
            if delay_seconds > 0 and i < len(videos) - 1:
                logger.info(f"Waiting {delay_seconds}s before next upload...")
                time.sleep(delay_seconds)
        
        logger.info(f"\n=== Upload Summary ===")
        logger.info(f"Successful: {len(results['successful'])}")
        logger.info(f"Failed: {len(results['failed'])}")
        
        return results


if __name__ == "__main__":
    print("YouTube Uploader Test")
    print("=" * 80)
    print("\n⚠️  First time setup required!")
    print("1. Create youtube_credentials.json (see YOUTUBE_SETUP.md)")
    print("2. Run this script")
    print("3. Browser will open for authentication")
    print("4. Grant permissions")
    print("5. Token will be saved for future use\n")
    
    try:
        uploader = YouTubeUploader()
        print("\n✓ Authentication successful!")
        print("Ready to upload videos to YouTube Shorts")
    except FileNotFoundError:
        print("\n✗ Setup incomplete - please create youtube_credentials.json first")
    except Exception as e:
        print(f"\n✗ Error: {e}")
