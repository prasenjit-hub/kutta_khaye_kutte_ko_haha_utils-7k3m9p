"""
YouTube Channel Scraper
Scrapes all videos from a YouTube channel without using API
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_channel_videos(channel_url: str, sort_by: str = 'date') -> List[Dict]:
    """
    Scrape all videos from a YouTube channel and sort
    
    Args:
        channel_url: YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)
        sort_by: 'date' for newest first, 'views' for highest views first
    
    Returns:
        List of video dictionaries with id, title, views, duration, upload_date
    """
    logger.info(f"Scraping channel: {channel_url}")
    
    # Ensure URL ends with /videos
    if not channel_url.endswith('/videos'):
        channel_url = channel_url.rstrip('/') + '/videos'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(channel_url, headers=headers)
        response.raise_for_status()
        
        # Extract initial data from page
        videos = extract_videos_from_page(response.text)
        
        logger.info(f"Found {len(videos)} videos")
        
        # Sort by date (newest first) or views (highest first)
        if sort_by == 'date':
            # Videos are already in chronological order (newest first) from YouTube
            logger.info("Sorted by upload date (newest first)")
        else:
            # Sort by views (highest first)
            videos.sort(key=lambda x: x.get('views', 0), reverse=True)
            logger.info("Sorted by views (highest first)")
        
        return videos
        
    except Exception as e:
        logger.error(f"Error scraping channel: {e}")
        return []


def extract_videos_from_page(html_content: str) -> List[Dict]:
    """
    Extract video information from YouTube page HTML
    """
    videos = []
    
    # Look for ytInitialData JSON in the page
    match = re.search(r'var ytInitialData = ({.*?});', html_content)
    if not match:
        logger.warning("Could not find ytInitialData in page")
        return videos
    
    try:
        data = json.loads(match.group(1))
        
        # Navigate through the nested JSON structure
        tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
        
        for tab in tabs:
            tab_renderer = tab.get('tabRenderer', {})
            if tab_renderer.get('selected'):
                contents = tab_renderer.get('content', {}).get('richGridRenderer', {}).get('contents', [])
                
                for item in contents:
                    video_renderer = item.get('richItemRenderer', {}).get('content', {}).get('videoRenderer', {})
                    
                    if video_renderer:
                        video_id = video_renderer.get('videoId')
                        title = video_renderer.get('title', {}).get('runs', [{}])[0].get('text', '')
                        
                        # Extract view count
                        view_text = video_renderer.get('viewCountText', {}).get('simpleText', '0')
                        views = parse_view_count(view_text)
                        
                        # Extract duration
                        duration_text = video_renderer.get('lengthText', {}).get('simpleText', '')
                        
                        # Extract upload time (e.g., "2 days ago", "1 week ago")
                        publish_time = video_renderer.get('publishedTimeText', {}).get('simpleText', 'Unknown')
                        
                        if video_id and title:
                            videos.append({
                                'id': video_id,
                                'title': title,
                                'views': views,
                                'duration': duration_text,
                                'published': publish_time,
                                'url': f'https://www.youtube.com/watch?v={video_id}'
                            })
        
    except Exception as e:
        logger.error(f"Error parsing video data: {e}")
    
    return videos


def parse_view_count(view_text: str) -> int:
    """
    Parse view count text like "1.2M views" to integer
    """
    try:
        # Remove "views" and clean
        view_text = view_text.lower().replace('views', '').replace('view', '').strip()
        
        # Handle K, M, B suffixes
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        
        for suffix, multiplier in multipliers.items():
            if suffix in view_text:
                number = float(view_text.replace(suffix, '').strip())
                return int(number * multiplier)
        
        # No suffix, just a number
        return int(view_text.replace(',', ''))
        
    except:
        return 0


if __name__ == "__main__":
    # Test the scraper
    test_url = "https://www.youtube.com/@MrBeast"
    videos = get_channel_videos(test_url)
    
    print(f"\nTop 5 videos by views:")
    for i, video in enumerate(videos[:5], 1):
        print(f"{i}. {video['title']}")
        print(f"   Views: {video['views']:,} | Duration: {video['duration']}")
        print(f"   URL: {video['url']}\n")
