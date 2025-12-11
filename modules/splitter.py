"""
Video Splitter
Splits videos into 1-minute segments
"""
from moviepy.editor import VideoFileClip
import os
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoSplitter:
    def __init__(self, output_dir: str = "processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def split_video(self, video_path: str, video_id: str, segment_duration: int = 60) -> List[str]:
        """
        Split video into segments of specified duration
        
        Args:
            video_path: Path to input video
            video_id: Video ID for naming segments
            segment_duration: Duration of each segment in seconds (default 60)
        
        Returns:
            List of paths to segment files
        """
        segment_paths = []
        
        try:
            logger.info(f"Loading video: {video_path}")
            video = VideoFileClip(video_path)
            total_duration = video.duration
            
            logger.info(f"Video duration: {total_duration:.2f}s")
            logger.info(f"Creating {segment_duration}s segments...")
            
            segment_num = 1
            start_time = 0
            
            while start_time < total_duration:
                end_time = min(start_time + segment_duration, total_duration)
                
                # Create segment
                segment = video.subclip(start_time, end_time)
                
                # Output path
                segment_filename = f"{video_id}_part{segment_num}.mp4"
                segment_path = os.path.join(self.output_dir, segment_filename)
                
                # Write segment
                logger.info(f"Writing segment {segment_num}: {start_time:.2f}s - {end_time:.2f}s")
                segment.write_videofile(
                    segment_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=f'temp-audio-{segment_num}.m4a',
                    remove_temp=True,
                    verbose=False,
                    fps=30
                )
                
                segment_paths.append(segment_path)
                segment.close()
                
                start_time = end_time
                segment_num += 1
            
            video.close()
            logger.info(f"Created {len(segment_paths)} segments")
            
            return segment_paths
            
        except Exception as e:
            logger.error(f"Error splitting video: {e}")
            return []
    
    def get_segment_info(self, video_path: str, segment_duration: int = 60) -> dict:
        """
        Get information about how many segments will be created
        """
        try:
            video = VideoFileClip(video_path)
            total_duration = video.duration
            num_segments = int(total_duration / segment_duration) + (1 if total_duration % segment_duration > 0 else 0)
            video.close()
            
            return {
                'total_duration': total_duration,
                'num_segments': num_segments,
                'segment_duration': segment_duration
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}


if __name__ == "__main__":
    # Test splitter
    splitter = VideoSplitter()
    
    # Test with downloaded video
    test_video = "downloads/test_video.mp4"
    if os.path.exists(test_video):
        segments = splitter.split_video(test_video, "test", segment_duration=60)
        print(f"\n✓ Created {len(segments)} segments:")
        for seg in segments:
            print(f"  - {seg}")
    else:
        print(f"\n✗ Test video not found: {test_video}")
