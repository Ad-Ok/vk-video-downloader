"""Default configuration for VK Video Downloader."""

from pathlib import Path

# --- Download settings ---
DOWNLOAD_DIR = Path("./downloads")
MAX_CONCURRENT = 3  # parallel downloads
FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
RATE_LIMIT = None  # e.g. "5M" for 5 MB/s, None = unlimited

# --- Auth ---
# Browser to extract cookies from: "chrome", "firefox", "edge", "safari", etc.
# Set to None to skip cookie extraction (public videos only)
COOKIES_BROWSER = "chrome"

# Alternative: path to a Netscape-format cookies.txt file
# Takes precedence over COOKIES_BROWSER if set
COOKIES_FILE = None  # e.g. Path("./cookies.txt")

# --- File naming ---
# Available placeholders: https://github.com/yt-dlp/yt-dlp#output-template
OUTPUT_TEMPLATE = "%(uploader)s/%(title)s [%(id)s].%(ext)s"

# --- Retry / resilience ---
RETRIES = 5
FRAGMENT_RETRIES = 5
RETRY_SLEEP = 5  # seconds between retries

# --- Misc ---
WRITE_THUMBNAIL = True
WRITE_DESCRIPTION = False
EMBED_METADATA = True
ARCHIVE_FILE = Path("./downloaded.txt")  # tracks already-downloaded videos (skip dupes)
