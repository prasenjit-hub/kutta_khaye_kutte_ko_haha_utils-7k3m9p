"""
Video Splitter
Splits videos into 1-minute segments using FFmpeg subprocess for reliability
"""
import os
import subprocess
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting duration: {e}")
        return 0


class VideoSplitter:
    def __init__(self, output_dir: str = "processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def split_video(self, video_path: str, video_id: str, segment_duration: int = 60) -> List[str]:
        """
        Split video into segments of specified duration using FFmpeg directly.
        This is more reliable than moviepy's write_videofile.
        """
        segment_paths = []
        
        try:
            logger.info(f"Loading video: {video_path}")
            total_duration = get_video_duration(video_path)
            
            if total_duration <= 0:
                logger.error("Could not determine video duration")
                return []
            
            logger.info(f"Video duration: {total_duration:.2f}s")
            logger.info(f"Creating {segment_duration}s segments...")
            
            segment_num = 1
            start_time = 0
            
            while start_time < total_duration:
                end_time = min(start_time + segment_duration, total_duration)
                duration = end_time - start_time
                
                # Skip if segment is too short (< 10s)
                if duration < 10:
                    logger.info(f"Skipping final segment (too short: {duration:.2f}s)")
                    break
                
                # Output path
                segment_filename = f"{video_id}_part{segment_num}.mp4"
                segment_path = os.path.join(self.output_dir, segment_filename)
                
                # Build FFmpeg command
                logger.info(f"Writing segment {segment_num}: {start_time:.2f}s - {end_time:.2f}s")
                
                cmd = [
                    'ffmpeg', '-y',  # Overwrite output
                    '-ss', str(start_time),  # Start time (before -i for fast seek)
                    '-i', video_path,  # Input file
                    '-t', str(duration),  # Duration
                    '-c:v', 'libx264',  # Video codec
                    '-preset', 'slow',  # Good quality encoding
                    '-c:a', 'aac',  # Audio codec
                    '-b:a', '256k',  # Good audio quality
                    '-movflags', '+faststart',  # Web optimization
                    '-loglevel', 'error',  # Only show errors
                    segment_path
                ]
                
                # Run FFmpeg
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error for segment {segment_num}: {result.stderr}")
                    continue
                
                # Verify output
                if os.path.exists(segment_path) and os.path.getsize(segment_path) > 1000:
                    segment_paths.append(segment_path)
                    logger.info(f"✓ Segment {segment_num} created successfully")
                else:
                    logger.error(f"Segment creation failed (file missing or too small): {segment_path}")
                
                start_time = end_time
                segment_num += 1
            
            logger.info(f"Created {len(segment_paths)} segments")
            return segment_paths
            
        except Exception as e:
            logger.error(f"Error splitting video: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_segment_info(self, video_path: str, segment_duration: int = 60) -> dict:
        """Get information about how the video would be split"""
        try:
            total_duration = get_video_duration(video_path)
            
            if total_duration <= 0:
                return {}
            
            num_segments = int(total_duration / segment_duration)
            # Add one more if there's a remainder >= 10 seconds
            remainder = total_duration % segment_duration
            if remainder >= 10:
                num_segments += 1
            
            return {
                'total_duration': total_duration,
                'num_segments': num_segments,
                'segment_duration': segment_duration
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}


if __name__ == "__main__":
    # Quick test
    splitter = VideoSplitter(output_dir="test_output")
    
    # Test with a video if exists
    test_video = "downloads/8bMh8azh3CY.mp4"
    if os.path.exists(test_video):
        info = splitter.get_segment_info(test_video)
        print(f"Video info: {info}")
        
        # Split first 60 seconds only for testing
        segments = splitter.split_video(test_video, "test_split", segment_duration=60)
        print(f"Created segments: {segments}")
    else:
        print("No test video found")
