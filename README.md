# YouTube to YouTube Shorts Automation 🎬

Automatic YouTube video downloader aur YouTube Shorts uploader. YouTube channel se highest viewed videos download karke, unhe 1-minute segments mein cut karke, Part 1/2/3 overlay add karke, YouTube Shorts pe auto-upload karta hai.

## ✅ Why YouTube Shorts?

- **100% Safe** - Official YouTube API use karta hai
- **No Ban Risk** - Google approved method
- **Monetization** - YouTube Shorts Fund se paisa mil sakta hai
- **Unlimited Uploads** - Quota increase request free hai
- **Scheduling Support** - Apna custom schedule set kar sakte ho

## 🚀 Features

- ✅ YouTube channel scraping (without API)
- ✅ Automatic 1080p video + audio download
- ✅ 1-minute segment splitting
- ✅ Part number overlay (Part 1, Part 2, etc.)
- ✅ Title overlay
- ✅ YouTube Shorts format (9:16)
- ✅ Auto upload to YouTube Shorts
- ✅ Download tracking (already downloaded videos skip hote hain)
- ✅ Views-based priority (highest views first)
- ✅ Official YouTube API (safe & legal)

## 📋 Requirements

- Python 3.8+
- FFmpeg (video processing ke liye)
- Google Cloud Account (free)

## 🛠️ Installation

### Step 1: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

### Step 2: Install FFmpeg

FFmpeg download karo aur system PATH mein add karo:
- Download: https://ffmpeg.org/download.html
- Windows: https://www.gyan.dev/ffmpeg/builds/

### Step 3: YouTube API Setup

**Complete guide**: Read `YOUTUBE_SETUP.md` for detailed instructions

**Quick steps**:
1. Google Cloud Console → Create Project
2. Enable YouTube Data API v3
3. Create OAuth credentials
4. Download `youtube_credentials.json`
5. Authenticate (first time only)

**Time**: 10 minutes one-time setup

### Step 4: Configure Settings

`config.json` file edit karo:

```json
{
  "youtube_channel": "https://www.youtube.com/@CHANNEL_NAME"  // ← Target channel
}
```

## 📖 Usage

### First Time Setup

```powershell
# Authenticate with YouTube
python modules\youtube_uploader.py
# Browser open hoga → Login → Permission → Done!
```

### Full Automation (Recommended)

Ek command se everything automatically ho jayega:

```powershell
python main.py --full
```

Ye karega:
1. Channel scrape
2. Highest viewed video download
3. Video split + edit
4. YouTube Shorts upload

### Step-by-Step Mode

```powershell
# 1. Channel scrape karo
python main.py --scrape --channel "https://www.youtube.com/@ChannelName"

# 2. Status check karo
python main.py --status

# 3. Next video download karo
python main.py --download VIDEO_ID

# 4. Video process karo (split + edit)
python main.py --process VIDEO_ID

# 5. YouTube pe upload karo
python main.py --upload
```

### Useful Commands

```powershell
# Status dekhna
python main.py --status

# Sirf scrape karna (download nahi)
python main.py --scrape

# Specific video download
python main.py --download dQw4w9WgXcQ
```

## 📁 Project Structure

```
youtube shorts automation/
├── config.json                  # Settings
├── tracking.json                # Download/upload tracking
├── requirements.txt             # Python dependencies
├── main.py                      # Main script
├── YOUTUBE_SETUP.md            # YouTube API setup guide
├── youtube_credentials.json    # YouTube OAuth credentials (you create)
├── youtube_token.pickle        # Saved auth token (auto-created)
├── modules/
│   ├── scraper.py              # YouTube scraper
│   ├── downloader.py           # Video downloader
│   ├── splitter.py             # Video splitter
│   ├── editor.py               # Overlay editor
│   └── youtube_uploader.py     # YouTube uploader
├── downloads/                   # Downloaded videos
├── processed/                   # Edited segments
└── logs/                        # Execution logs
```

## ⚙️ Configuration Options

### YouTube Upload Settings

```json
"youtube_upload": {
  "title_template": "{title} - Part {part}",
  "description_template": "{title}\n\nPart {part} of {total}\n\n#Shorts",
  "tags": ["shorts", "viral", "trending"],
  "privacy_status": "public",           // public, private, unlisted
  "delay_between_uploads_seconds": 10   // Wait between uploads
}
```

### Video Settings

```json
"video_settings": {
  "segment_duration_seconds": 60,      // Segment length
  "max_segments_per_video": 10,        // Max parts per video
  "target_resolution": [1080, 1920],   // YouTube Shorts resolution
  "aspect_ratio": "9:16"               // Portrait mode
}
```

### Overlay Settings

```json
"overlay_settings": {
  "part_text_format": "Part {n}",      // "Part 1", "Part 2"
  "part_text_size": 80,                // Font size
  "title_text_size": 50,               // Title font size
  "text_color": [255, 255, 255]        // White text
}
```

## 🔍 Tracking System

`tracking.json` file automatically maintain hoti hai:

```json
{
  "videos": {
    "VIDEO_ID": {
      "title": "Video Title",
      "views": 1000000,
      "status": "completed",              // pending/downloaded/processed/completed
      "parts_uploaded": [1, 2, 3],
      "youtube_video_ids": ["abc123", "def456"],
      "downloaded_at": "2025-12-10",
      "last_upload": "2025-12-10"
    }
  }
}
```

## 📊 YouTube API Quota

| Quota Level | Uploads/Day | How to Get |
|-------------|-------------|------------|
| **Default** | ~6 | Automatic (free) |
| **Increased** | ~60 | Request (free, 24-48hr) |
| **High** | ~600 | Support request (free) |

**Quota increase kaise kare**: See `YOUTUBE_SETUP.md`

## 🛡️ Safety & Legal

- ✅ **100% Safe** - Official YouTube API
- ✅ **No Ban Risk** - Google approved
- ✅ **Legal** - Follows YouTube TOS
- ✅ **Monetizable** - YouTube Shorts Fund eligible
- ⚠️ **Copyright** - Only upload content you have rights to

## 🐛 Troubleshooting

### YouTube Authentication Failed
```
Solution: 
*************
```

### FFmpeg Not Found
```
Solution: Install FFmpeg and add to PATH
```

### Quota Exceeded
```
Solution: 
- Request quota increase (free, 24-48hr)
- Or wait until next day (quota resets daily)
```

### Video Download Failed
```
Solution:
- Internet connection check karo
- YouTube URL verify karo
- yt-dlp update karo: pip install -U yt-dlp
```

## 📝 Example Workflow

```powershell
# 1. YouTube API Setup (one-time, 10 min)
# Follow YOUTUBE_SETUP.md

# 2. First authentication
python modules\youtube_uploader.py

# 3. Configure channel
# Edit config.json → Set youtube_channel

# 4. Run automation
python main.py --full

# 5. Monitor
python main.py --status
```

## 🔄 Automation Schedule

Windows Task Scheduler use karke daily automation:

```powershell
# Create scheduled task
schtasks /create /tn "YouTube Shorts Upload" /tr "python Z:\testing\instagram auto video upload\main.py --full" /sc daily /st 10:00
```

Or use your own scheduling system!

## 📊 Logs

Sab kuch log hota hai:
- `logs/automation.log` - Main execution log
- Real-time console output

## ❓ FAQ

**Q: Kitne Shorts upload kar sakte hain per day?**
A: Default 6, quota increase ke baad 60+

**Q: Kya safe hai?**
A: 100% safe! Official YouTube API hai.

**Q: API key kaise milega?**
A: Free! Google Cloud Console se. Guide: `YOUTUBE_SETUP.md`

**Q: Monetization milega?**
A: Haan! YouTube Shorts Fund eligible hai.

**Q: Scheduling kar sakte hain?**
A: Haan! Apna custom schedule set karo.

## 🎯 Comparison: This vs Manual

| Task | Manual | Automated |
|------|--------|-----------|
| Download video | 5 min | Auto |
| Split into parts | 30 min | Auto |
| Add overlays | 1 hr | Auto |
| Upload 10 shorts | 30 min | Auto |
| **Total** | **~2 hours** | **5 minutes** |

## 📞 Support

Issues face kar rahe ho? Check karo:
1. `logs/automation.log` file
2. `YOUTUBE_SETUP.md` guide
3. Console output
4. YouTube OAuth consent screen settings

## 🎯 Roadmap

- [x] YouTube Shorts upload
- [x] Automatic tracking
- [x] Batch processing
- [ ] Thumbnail generation
- [ ] Analytics tracking
- [ ] Web UI dashboard
- [ ] Multiple channels support

---

**Made with ❤️ for YouTube creators**

✅ **100% Safe & Legal** - Uses official YouTube API
