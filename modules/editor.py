"""
Video Editor
Adds text overlays and converts to YouTube Shorts format (9:16)
Supports Split Screen (Gameplay Bottom) to avoid reused content issues
"""
import subprocess
import os
import logging
import random
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
        self.split_screen_config = self.video_settings.get('split_screen', {'enabled': False})
    
    def _create_text_overlay(self, text: str, width: int, height: int = 200) -> str:
        """Create a text overlay image using PIL"""
        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw SOLID BLACK background strip for text (Header style)
        header_height = 180
        draw.rectangle([(0, 0), (width, header_height)], fill=(0, 0, 0, 255))
        
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
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
        except AttributeError:
            bbox = draw.textsize(text, font=font)
            bbox = (0, 0, bbox[0], bbox[1])

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text vertically in the header strip
        x = (width - text_width) // 2
        y = (header_height - text_height) // 2 - 10 # Slightly up adjustment
        
        # Draw shadow
        shadow_offset = 3
        for ox in [-shadow_offset, 0, shadow_offset]:
            for oy in [-shadow_offset, 0, shadow_offset]:
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, font=font, fill=(50, 50, 50, 255))
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        # Save to temp file
        overlay_path = 'temp_overlay.png'
        img.save(overlay_path)
        
        return overlay_path
    
    def _get_random_gameplay(self, duration: float):
        """Find a gameplay video and get random start time"""
        folder = self.split_screen_config.get('gameplay_folder', 'assets/gameplay')
        
        if not os.path.exists(folder):
            logger.warning(f"Gameplay folder not found: {folder}")
            return None, 0
            
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(('.mp4', '.mkv', '.mov'))]
        
        if not files:
            logger.warning("No gameplay videos found!")
            return None, 0
            
        gameplay_path = random.choice(files)
        
        # Get its duration
        gp_info = get_video_info(gameplay_path)
        gp_duration = gp_info['duration']
        
        if gp_duration <= duration:
            start_time = 0
        else:
            # Random start, ensuring we have enough duration left
            max_start = gp_duration - duration
            start_time = random.uniform(0, max_start)
            
        logger.info(f"Selected gameplay: {gameplay_path} (Start: {start_time:.2f}s)")
        return gameplay_path, start_time

    def add_overlays(self, video_path: str, part_number: int, title: str, output_path: str = None) -> str:
        """
        Add text overlays and convert to proper format (Split Screen or Blur Background)
        """
        if output_path is None:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_edited{ext}"
        
        try:
            logger.info(f"Processing video: {video_path}")
            
            if not os.path.exists(video_path):
                logger.error(f"Input file not found: {video_path}")
                return None
            
            # Get main video info
            video_info = get_video_info(video_path)
            input_width = video_info['width']
            input_height = video_info['height']
            duration = video_info['duration']
            
            # Target resolution
            target_width, target_height = self.video_settings.get('target_resolution', [1080, 1920])
            
            # Create text overlay
            part_text = self.overlay_settings.get('part_text_format', 'Part {n}').format(n=part_number)
            overlay_path = self._create_text_overlay(part_text, target_width, target_height) # Pass full height
            
            # CHECK SPLIT SCREEN
            use_split_screen = self.split_screen_config.get('enabled', False)
            gameplay_path = None
            gameplay_start = 0
            
            if use_split_screen:
                gameplay_path, gameplay_start = self._get_random_gameplay(duration)
                if not gameplay_path:
                    logger.warning("Falling back to blur background mode")
                    use_split_screen = False
            
            # BUILD FFMPEG COMMAND
            cmd = ['ffmpeg', '-y']
            
            # Input 0: Main Video
            cmd.extend(['-i', video_path])
            
            # Input 1: Gameplay (if split screen) or Overlay (if blur)
            if use_split_screen:
                # Need to add gameplay file with seek
                cmd.extend(['-ss', str(gameplay_start), '-t', str(duration), '-i', gameplay_path])
                # Input 2: Overlay
                cmd.extend(['-i', overlay_path])
                
                # Filter for Split Screen
                filter_complex = self._build_filter_split_screen(target_width, target_height)
                # Map audio from main video only (0:a)
                map_args = ['-map', '[v_out]', '-map', '0:a']
                
            else:
                # Input 1: Overlay
                cmd.extend(['-i', overlay_path])
                
                # Filter for Blur Background
                filter_complex = self._build_filter_with_blur_background(
                    input_width, input_height, target_width, target_height
                )
                map_args = ['-map', '[outv]', '-map', '0:a?']

            # Common options
            cmd.extend([
                '-filter_complex', filter_complex,
                *map_args,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '256k',
                '-r', '30',
                '-movflags', '+faststart',
                '-loglevel', 'error',
                output_path
            ])
            
            logger.info(f"Running FFmpeg...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Cleanup temp overlay
            if os.path.exists(overlay_path):
                os.remove(overlay_path)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"✓ Video processed successfully")
                return output_path
            else:
                logger.error("Output file missing or too small")
                return None
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_filter_split_screen(self, out_w: int, out_h: int) -> str:
        """
        Builds filter for:
        Header: 180px reserved (Black)
        Content Height: out_h - 180
        Top: Main Video (70% of content)
        Bottom: Gameplay (30% of content)
        """
        header_h = 180
        available_h = out_h - header_h
        
        top_pct = self.split_screen_config.get('top_video_height_percentage', 0.70)
        
        top_h = int(available_h * top_pct)
        # Ensure even number
        if top_h % 2 != 0: top_h -= 1
            
        bottom_h = available_h - top_h
        
        # [0:v] is main, [1:v] is gameplay, [2:v] is overlay
        
        filter_complex = (
            # 1. Scale and Crop Main Video (Top) - WITH HORIZONTAL FLIP
            f"[0:v]hflip,scale={out_w}:{top_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{top_h}[top];"
            
            # 2. Scale and Crop Gameplay (Bottom)
            f"[1:v]scale={out_w}:{bottom_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{bottom_h}[bottom];"
            
            # 3. Stack them (Total height = available_h)
            f"[top][bottom]vstack[stacked];"
            
            # 4. Pad top to make space for header (push content down)
            f"[stacked]pad={out_w}:{out_h}:0:{header_h}:black[padded];"
            
            # 5. Add Overlay (Text on header)
            f"[padded][2:v]overlay=(W-w)/2:0[v_out]"
        )
        return filter_complex

    def _build_filter_with_blur_background(self, in_w: int, in_h: int, out_w: int, out_h: int) -> str:
        """Fallback filter for blur background mode"""
        target_aspect = out_w / out_h
        current_aspect = in_w / in_h
        
        if current_aspect > target_aspect:
            filter_complex = (
                "[0:v]split=2[bg_in][fg_in];"
                f"[bg_in]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                "gblur=sigma=18,"
                "eq=brightness=-0.3:saturation=0.5"
                "[bg];"
                f"[fg_in]scale={out_w}:-2[fg_scaled];"
                "[bg][fg_scaled]overlay=(W-w)/2:(H-h)/2[video_out];"
                "[video_out][1:v]overlay=(W-w)/2:0[outv]"
            )
        else:
            if current_aspect < target_aspect:
                filter_complex = (
                    f"[0:v]scale={out_w}:-2,crop={out_w}:{out_h}[scaled];"
                    "[scaled][1:v]overlay=(W-w)/2:0[outv]"
                )
            else:
                filter_complex = (
                    f"[0:v]scale={out_w}:{out_h}[scaled];"
                    "[scaled][1:v]overlay=(W-w)/2:0[outv]"
                )
        return filter_complex


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
