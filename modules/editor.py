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


class VideoEditor:
    def __init__(self, config: dict):
        self.config = config
        self.overlay_settings = config.get('overlay_settings', {})
        self.video_settings = config.get('video_settings', {})
    
    def add_overlays(self, video_path: str, part_number: int, title: str, output_path: str = None) -> str:
        """
        Add text overlays to video and convert to YouTube Shorts format
        
        Args:
            video_path: Path to input video segment
            part_number: Part number for overlay
            title: Video title (for filename only, not displayed on video)
            output_path: Optional custom output path
        
        Returns:
            Path to edited video
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
            from PIL import Image, ImageDraw, ImageFont
            
            # Create transparent image for text
            txt_img = Image.new('RGBA', (video.w, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_img)
            
            # Try to use a nice font, fallback to default
            try:
                font_size = self.overlay_settings.get('part_text_size', 80)
                # Try Arial Bold (Windows)
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except:
                try:
                    # Fallback to regular Arial
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    # Use default font
                    font = ImageFont.load_default()
            
            # Get text size for centering
            bbox = draw.textbbox((0, 0), part_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
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
                verbose=False
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
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_to_reels_format(self, video: VideoFileClip) -> VideoFileClip:
        """
        Convert video to 9:16 aspect ratio (1080x1920) for YouTube Shorts
        
        For landscape videos: Resize to fit WIDTH, add blur background padding
        This keeps all content visible without aggressive cropping
        """
        target_width, target_height = self.video_settings.get('target_resolution', [1080, 1920])
        target_aspect = target_width / target_height  # 9:16 = 0.5625
        current_aspect = video.w / video.h
        
        if abs(current_aspect - target_aspect) < 0.01:
            # Already correct aspect ratio, just resize
            return video.resize(height=target_height)
        
        if current_aspect > target_aspect:
            # Video is LANDSCAPE (wider) - needs portrait conversion
            # Strategy: Fit by WIDTH, add padding top/bottom
            
            # Resize video to fit target width
            video_resized = video.resize(width=target_width)
            
            # Now video.w = 1080, but video.h might be less than 1920
            # We need to add padding (background) to make it 1920
            
            if video_resized.h < target_height:
                # Need to add padding on top and bottom
                from moviepy.editor import ColorClip, CompositeVideoClip
                
                # Create blurred background (optional - or use black)
                # For now, let's use a blurred, darkened version of the video itself
                background = video_resized.resize(height=target_height)  # This will be wider
                background = background.resize(0.5)  # Make it smaller
                background = background.resize(height=target_height)  # Scale back up (creates blur effect)
                
                # Darken the background
                background = background.fl_image(lambda image: (image * 0.3).astype('uint8'))
                
                # Center the main video
                y_offset = (target_height - video_resized.h) // 2
                
                # Composite: background + centered video
                final = CompositeVideoClip([
                    background.set_position(('center', 'center')),
                    video_resized.set_position(('center', y_offset))
                ], size=(target_width, target_height))
                
                return final
            else:
                # Video is already taller after width resize, just crop
                y_center = video_resized.h / 2
                y1 = int(y_center - target_height / 2)
                return video_resized.crop(y1=y1, height=target_height)
        else:
            # Video is already PORTRAIT (taller than target)
            # Fit by width and crop height
            video = video.resize(width=target_width)
            
            if video.h > target_height:
                y_center = video.h / 2
                y1 = int(y_center - target_height / 2)
                video = video.crop(y1=y1, height=target_height)
            
            return video
    
    def _truncate_title(self, title: str, max_length: int = 40) -> str:
        """
        Truncate title if too long
        """
        if len(title) <= max_length:
            return title
        return title[:max_length-3] + '...'


if __name__ == "__main__":
    # Test editor
    import json
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    editor = VideoEditor(config)
    
    # Test with a segment
    test_segment = "processed/test_part1.mp4"
    if os.path.exists(test_segment):
        result = editor.add_overlays(
            test_segment,
            part_number=1,
            title="Test Video Title for Instagram Reels"
        )
        if result:
            print(f"\n✓ Edited video created: {result}")
    else:
        print(f"\n✗ Test segment not found: {test_segment}")
