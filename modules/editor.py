"""
Video Editor
Adds text overlays (part numbers) and converts to YouTube Shorts format (9:16)
Uses FFmpeg for reliable video processing with blur background for landscape videos
"""
import subprocess
import os
import logging
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_video_info(video_path: str) -> dict:
    """Get video dimensions and duration using ffprobe"""
    try:
        # Get video stream info
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0:s=x',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        dimensions = result.stdout.strip().split('x')
        
        width = int(dimensions[0]) if dimensions[0] else 1920
        height = int(dimensions[1]) if len(dimensions) > 1 and dimensions[1] else 1080
        
        # Get duration
        cmd_dur = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
        duration = float(result_dur.stdout.strip()) if result_dur.stdout.strip() else 60
        
        return {'width': width, 'height': height, 'duration': duration}
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {'width': 1920, 'height': 1080, 'duration': 60}


class VideoEditor:
    def __init__(self, config: dict):
        self.config = config
        self.overlay_settings = config.get('overlay_settings', {})
        self.video_settings = config.get('video_settings', {})
    
    def _create_text_overlay(self, text: str, width: int, height: int = 200) -> str:
        """Create a text overlay image using PIL"""
        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load font
        font_size = self.overlay_settings.get('part_text_size', 80)
        font = None
        
        font_paths = [
            "arialbd.ttf",
            "arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        # Center text
        x = (width - text_width) // 2
        y = 50
        
        # Draw shadow
        shadow_offset = 3
        for ox in [-shadow_offset, 0, shadow_offset]:
            for oy in [-shadow_offset, 0, shadow_offset]:
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, 255))
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        # Save to temp file
        overlay_path = 'temp_overlay.png'
        img.save(overlay_path)
        
        return overlay_path
    
    def add_overlays(self, video_path: str, part_number: int, title: str, output_path: str = None) -> str:
        """
        Add text overlays to video and convert to YouTube Shorts format (9:16)
        For landscape videos: Adds blur background (not crop/zoom) to keep full content visible
        """
        if output_path is None:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_edited{ext}"
        
        try:
            logger.info(f"Adding overlays to: {video_path}")
            
            # Verify input exists
            if not os.path.exists(video_path):
                logger.error(f"Input file not found: {video_path}")
                return None
            
            # Get video info
            video_info = get_video_info(video_path)
            input_width = video_info['width']
            input_height = video_info['height']
            
            logger.info(f"Input video: {input_width}x{input_height}")
            
            # Target resolution (9:16 for YouTube Shorts)
            target_width, target_height = self.video_settings.get('target_resolution', [1080, 1920])
            
            # Create text overlay
            part_text = self.overlay_settings.get('part_text_format', 'Part {n}').format(n=part_number)
            overlay_path = self._create_text_overlay(part_text, target_width)
            
            # Build FFmpeg filter for 9:16 conversion
            # For landscape videos: Use blur background padding (like old editor)
            filter_complex = self._build_filter_with_blur_background(
                input_width, input_height,
                target_width, target_height
            )
            
            # FFmpeg command
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,  # Input video
                '-i', overlay_path,  # Overlay image
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '0:a?',  # Keep audio if exists
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '256k',
                '-r', '30',  # 30 fps
                '-movflags', '+faststart',
                '-loglevel', 'error',
                output_path
            ]
            
            logger.info(f"Writing edited video to: {output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Cleanup temp overlay
            if os.path.exists(overlay_path):
                os.remove(overlay_path)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
            
            # Verify output
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"✓ Overlay added successfully")
                return output_path
            else:
                logger.error("Output file missing or too small")
                return None
                
        except Exception as e:
            logger.error(f"Error adding overlays: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_filter_with_blur_background(self, in_w: int, in_h: int, out_w: int, out_h: int) -> str:
        """
        Build FFmpeg filter complex for 9:16 conversion with BLUR BACKGROUND
        
        For landscape videos:
        1. Create a blurred, darkened copy as background
        2. Resize original to fit width
        3. Center original on blurred background
        4. Add text overlay on top
        
        This keeps ALL content visible without zooming/cropping!
        """
        target_aspect = out_w / out_h  # 9:16 = 0.5625
        current_aspect = in_w / in_h
        
        if current_aspect > target_aspect:
            # LANDSCAPE video - needs blur background padding
            # 
            # Filter explanation:
            # [0:v] - Input video
            # split - Make 2 copies
            # [bg] - Background copy: scale to fill, blur heavily, darken
            # [fg] - Foreground copy: scale to fit width, center vertically
            # overlay - Put foreground on background
            # [1:v] overlay - Add text overlay on top
            
            filter_complex = (
                # Split input into background and foreground
                "[0:v]split=2[bg_in][fg_in];"
                
                # Background: scale to fill 9:16, blur heavily, darken
                f"[bg_in]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                "gblur=sigma=18,"  # Moderate blur (not too heavy)
                "eq=brightness=-0.3:saturation=0.5"  # Darken and desaturate
                "[bg];"
                
                # Foreground: scale to fit width, keep aspect ratio
                f"[fg_in]scale={out_w}:-2[fg_scaled];"
                
                # Overlay foreground centered on background
                "[bg][fg_scaled]overlay=(W-w)/2:(H-h)/2[video_out];"
                
                # Add text overlay on top
                "[video_out][1:v]overlay=(W-w)/2:0[outv]"
            )
        else:
            # PORTRAIT or SQUARE video - simple scale and pad/crop
            if current_aspect < target_aspect:
                # Taller than target - scale to width, crop height
                filter_complex = (
                    f"[0:v]scale={out_w}:-2,crop={out_w}:{out_h}[scaled];"
                    "[scaled][1:v]overlay=(W-w)/2:0[outv]"
                )
            else:
                # Already correct aspect - just resize
                filter_complex = (
                    f"[0:v]scale={out_w}:{out_h}[scaled];"
                    "[scaled][1:v]overlay=(W-w)/2:0[outv]"
                )
        
        return filter_complex
    
    def _truncate_title(self, title: str, max_length: int = 40) -> str:
        if len(title) <= max_length:
            return title
        return title[:max_length-3] + '...'


if __name__ == "__main__":
    import json
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    editor = VideoEditor(config)
    
    # Test with a video if exists
    test_dir = "test_output"
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if f.endswith('.mp4') and not f.endswith('_edited.mp4'):
                input_path = os.path.join(test_dir, f)
                output_path = os.path.join(test_dir, f.replace('.mp4', '_edited.mp4'))
                
                print(f"Testing editor with: {input_path}")
                result = editor.add_overlays(input_path, 1, "Test Title", output_path)
                
                if result:
                    print(f"✓ Success: {result}")
                else:
                    print("✗ Failed")
                break
    else:
        print("No test_output directory found. Run splitter first.")
