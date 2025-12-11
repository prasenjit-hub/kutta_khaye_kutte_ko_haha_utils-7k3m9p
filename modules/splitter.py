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

# PrintingLogger to see FFmpeg output safely
class PrintingLogger:
    def __call__(self, message): 
        if message: print(f"[MoviePy] {message}")
    def tqdm(self, *args, **kwargs): return args[0]
    def write(self, message): 
        if message.strip(): print(f"[FFmpeg] {message.strip()}")
    def flush(self): pass
    def iter_bar(self, iterator=None, **kwargs): 
        if iterator:
            for x in iterator:
                yield x

class VideoSplitter:
    def __init__(self, output_dir: str = "processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def split_video(self, video_path: str, video_id: str, segment_duration: int = 60) -> List[str]:
        """
        Split video into segments of specified duration
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
                
                # Check for minimum duration (skip if < 10s)
                if (end_time - start_time) < 10:
                    break

                # Create segment
                segment = video.subclip(start_time, end_time)
                
                # Output path (Switching to MKV for stability)
                segment_filename = f"{video_id}_part{segment_num}.mkv"
                segment_path = os.path.join(self.output_dir, segment_filename)
                
                # Write segment
                logger.info(f"Writing segment {segment_num}: {start_time:.2f}s - {end_time:.2f}s")
                segment.write_videofile(
                    segment_path,
                    codec='libx264',
                    # audio_codec='aac', # Let automatic selection work for MKV
                    temp_audiofile=f'temp-audio-{segment_num}.m4a',
                    remove_temp=True,
                    verbose=True,
                    logger=PrintingLogger(),
                    fps=30,
                    threads=1,
                    preset='veryfast' # Slightly safer than ultrafast
                )
                
                segment_paths.append(segment_path)
                segment_path_abs = os.path.abspath(segment_path)
                if os.path.exists(segment_path_abs) and os.path.getsize(segment_path_abs) > 0:
                     logger.info(f"Verified segment exists: {segment_path}")
                else:
                     logger.error(f"Segment file creation failed or empty: {segment_path}")

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
    splitter = VideoSplitter()
