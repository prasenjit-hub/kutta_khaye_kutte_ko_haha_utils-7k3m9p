"""
Video Editor
Adds text overlays (part numbers, titles) and converts to Instagram Reel format
"""
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SilentLogger to prevent stdout errors in GitHub Actions
class SilentLogger:
    def __call__(self, message): pass
    def tqdm(self, *args, **kwargs): return args[0]
    def write(self, message): pass
    def flush(self): pass
    def iter_bar(self, **kwargs): pass
    def iterators(self, **kwargs): pass

class VideoEditor:
    def __init__(self, config: dict):
        self.config = config
        self.overlay_settings = config.get('overlay_settings', {})
        self.video_settings = config.get('video_settings', {})
    
    def add_overlays(self, video_path: str, part_number: int, title: str, output_path: str = None) -> str:
        """
        Add text overlays to video and convert to YouTube Shorts format
        """
        if output_path is None:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_edited{ext}"
        
        try:
            logger.info(f"Adding overlays to: {video_path}")
            
            # Load video
            video = VideoFileClip(video_path)
            
            # Convert to YouTube Shorts aspect ratio (9:16)
            video = self._convert_to_reels_format(video)
            
            # Create Part number overlay using PIL
            part_text = self.overlay_settings.get('part_text_format', 'Part {n}').format(n=part_number)
            
            # Create text overlay image using PIL
            # Create transparent image for text
            txt_img = Image.new('RGBA', (video.w, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_img)
            
            # Try to use a nice font, fallback to default
            try:
                font_size = self.overlay_settings.get('part_text_size', 80)
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
            
            # Get text size for centering
            bbox = draw.textbbox((0, 0), part_text, font=font)
            text_width = bbox[2] - bbox[0]
            
            x = (video.w - text_width) // 2
            y = 50
            
            # Draw shadow (black outline)
            shadow_offset = 3
            for offset_x in [-shadow_offset, 0, shadow_offset]:
                for offset_y in [-shadow_offset, 0, shadow_offset]:
                    if offset_x != 0 or offset_y != 0:
                        draw.text((x + offset_x, y + offset_y), part_text, font=font, fill=(0, 0, 0, 255))
            
            # Draw main text (white)
            draw.text((x, y), part_text, font=font, fill=(255, 255, 255, 255))
            
            # Save text overlay as temporary image
            txt_overlay_path = 'temp_text_overlay.png'
            txt_img.save(txt_overlay_path)
            
            # Create ImageClip from the text overlay
            from moviepy.editor import ImageClip
            text_clip = ImageClip(txt_overlay_path).set_duration(video.duration).set_position(('center', 0))
            
            # Composite video with text overlay
            final_video = CompositeVideoClip([video, text_clip])
            
            # Write output
            logger.info(f"Writing edited video to: {output_path}")
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=30,
                preset='medium',
                verbose=False,
                logger=SilentLogger()  # Use custom silent logger
            )
            
            # Cleanup
            video.close()
            final_video.close()
            
            # Remove temporary overlay image
            if os.path.exists(txt_overlay_path):
                os.remove(txt_overlay_path)
            
            logger.info(f"✓ Overlay added successfully")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding overlays: {e}")
            return None
    
    def _convert_to_reels_format(self, video: VideoFileClip) -> VideoFileClip:
        target_width, target_height = self.video_settings.get('target_resolution', [1080, 1920])
        target_aspect = target_width / target_height
        current_aspect = video.w / video.h
        
        if abs(current_aspect - target_aspect) < 0.01:
            return video.resize(height=target_height)
        
        if current_aspect > target_aspect:
            video_resized = video.resize(width=target_width)
            if video_resized.h < target_height:
                from moviepy.editor import CompositeVideoClip
                background = video_resized.resize(height=target_height)
                background = background.resize(0.5)
                background = background.resize(height=target_height)
                background = background.fl_image(lambda image: (image * 0.3).astype('uint8'))
                y_offset = (target_height - video_resized.h) // 2
                final = CompositeVideoClip([
                    background.set_position(('center', 'center')),
                    video_resized.set_position(('center', y_offset))
                ], size=(target_width, target_height))
                return final
            else:
                y_center = video_resized.h / 2
                y1 = int(y_center - target_height / 2)
                return video_resized.crop(y1=y1, height=target_height)
        else:
            video = video.resize(width=target_width)
            if video.h > target_height:
                y_center = video.h / 2
                y1 = int(y_center - target_height / 2)
                video = video.crop(y1=y1, height=target_height)
            return video
    
    def _truncate_title(self, title: str, max_length: int = 40) -> str:
        if len(title) <= max_length:
            return title
        return title[:max_length-3] + '...'

if __name__ == "__main__":
    import json
    with open('config.json', 'r') as f:
        config = json.load(f)
    editor = VideoEditor(config)
