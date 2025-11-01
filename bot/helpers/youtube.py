"""
YouTube helper for yt-dlp integration and music search/download.
"""
import asyncio
import logging
import tempfile
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)


class YouTubeHelper:
    """YouTube search and download helper."""
    
    def __init__(self, download_dir: Path):
        """Initialize YouTube helper."""
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'audioquality': '192',
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'writeskiplist': False,
        }
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        youtube_domains = [
            'youtube.com',
            'www.youtube.com',
            'm.youtube.com',
            'youtu.be',
            'www.youtu.be'
        ]
        
        try:
            parsed = urlparse(url)
            return parsed.netloc in youtube_domains
        except:
            return False
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for videos on YouTube."""
        try:
            search_opts = self.ydl_opts.copy()
            search_opts['format'] = 'bestaudio/best'
            search_opts['noplaylist'] = True
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                # Search for videos
                search_query = f"ytsearch{limit}:{query}"
                results = ydl.extract_info(search_query, download=False)
                
                videos = []
                if 'entries' in results:
                    for entry in results['entries']:
                        if entry:
                            videos.append({
                                'id': entry.get('id'),
                                'title': entry.get('title', 'Unknown'),
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'thumbnail': entry.get('thumbnail'),
                                'webpage_url': entry.get('webpage_url'),
                                'view_count': entry.get('view_count', 0),
                            })
                
                logger.info(f"Found {len(videos)} videos for query: {query}")
                return videos
                
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                return {
                    'id': info.get('id'),
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', ''),
                }
                
        except Exception as e:
            logger.error(f"Failed to get video info for {url}: {e}")
            return None
    
    async def download_audio(self, url: str) -> Optional[Dict[str, Any]]:
        """Download audio from URL."""
        try:
            # Create a temporary file for download
            with tempfile.NamedTemporaryFile(
                suffix='.mp3', 
                dir=self.download_dir, 
                delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
            
            download_opts = self.ydl_opts.copy()
            download_opts['outtmpl'] = str(temp_path.with_suffix('.%(ext)s'))
            
            logger.info(f"Starting download: {url}")
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    return None
                
                # Find the downloaded file
                downloaded_files = list(self.download_dir.glob(f"*{info.get('id', '')}*"))
                if not downloaded_files:
                    downloaded_files = list(self.download_dir.glob("*.mp3"))
                    # Sort by modification time and get the most recent
                    downloaded_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    if downloaded_files:
                        temp_path = downloaded_files[0]
                
                # Get the actual file path
                if temp_path.exists():
                    file_path = temp_path
                else:
                    # Try to find by ID
                    id_pattern = f"*{info.get('id', '')}*"
                    matching_files = list(self.download_dir.glob(id_pattern))
                    if matching_files:
                        file_path = matching_files[0]
                    else:
                        logger.error("Downloaded file not found")
                        return None
                
                track_info = {
                    'file_path': str(file_path),
                    'title': info.get('title', 'Unknown'),
                    'artist': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'source_url': url,
                    'video_id': info.get('id'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')
                }
                
                logger.info(f"Successfully downloaded: {track_info['title']}")
                return track_info
                
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            return None
    
    async def handle_url(self, url_or_query: str) -> Optional[Dict[str, Any]]:
        """Handle URL or search query."""
        if self.is_youtube_url(url_or_query):
            # Direct URL
            info = await self.get_video_info(url_or_query)
            if info:
                # Download the audio
                return await self.download_audio(url_or_query)
            else:
                return None
        else:
            # Search query
            search_results = await self.search(url_or_query, limit=1)
            if search_results:
                video = search_results[0]
                download_url = f"https://www.youtube.com/watch?v={video['id']}"
                return await self.download_audio(download_url)
            else:
                return None
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old downloaded files."""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.download_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            logger.info(f"Cleaned up old file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to clean up {file_path}: {e}")
                            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def validate_url(self, url: str) -> bool:
        """Validate YouTube URL."""
        if not self.is_youtube_url(url):
            return False
        
        video_id = self.extract_video_id(url)
        return video_id is not None
