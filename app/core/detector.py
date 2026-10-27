import re
from enum import Enum
from typing import Dict, Any

class Platform(str, Enum):
    YOUTUBE = "youtube"
    YT_MUSIC = "yt_music"
    SPOTIFY = "spotify"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TWITTER = "twitter"
    SOUNDCLOUD = "soundcloud"
    PINTEREST = "pinterest"
    FACEBOOK = "facebook"
    REDDIT = "reddit"
    BILIBILI = "bilibili"
    VIMEO = "vimeo"
    DAILYMOTION = "dailymotion"
    TWITCH = "twitch"
    GENERIC = "generic"

class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    CAROUSEL = "carousel"
    PLAYLIST = "playlist"
    UNKNOWN = "unknown"

def detect_platform(url: str) -> Dict[str, Any]:
    """Mendeteksi platform dan kemungkinan jenis konten dari sebuah URL."""
    clean_url = url.strip()
    
    # 1. Spotify
    if "open.spotify.com" in clean_url or clean_url.startswith("spotify:"):
        media_type = MediaType.AUDIO
        if "/playlist/" in clean_url:
            media_type = MediaType.PLAYLIST
        elif "/album/" in clean_url:
            media_type = MediaType.PLAYLIST
        elif "/track/" in clean_url:
            media_type = MediaType.AUDIO
            
        return {
            "platform": Platform.SPOTIFY,
            "name": "Spotify",
            "media_type": media_type,
            "url": clean_url
        }
        
    # 2. YouTube Music
    if "music.youtube.com" in clean_url:
        media_type = MediaType.AUDIO
        if "list=" in clean_url:
            media_type = MediaType.PLAYLIST
        return {
            "platform": Platform.YT_MUSIC,
            "name": "YouTube Music",
            "media_type": media_type,
            "url": clean_url
        }

    # 3. YouTube Regular
    if any(domain in clean_url for domain in ["youtube.com", "youtu.be"]):
        media_type = MediaType.VIDEO
        if "playlist" in clean_url or "list=" in clean_url:
            media_type = MediaType.PLAYLIST
        elif "/shorts/" in clean_url:
            media_type = MediaType.VIDEO
        return {
            "platform": Platform.YOUTUBE,
            "name": "YouTube",
            "media_type": media_type,
            "url": clean_url
        }

    # 4. TikTok
    if any(domain in clean_url for domain in ["tiktok.com", "vt.tiktok.com", "vm.tiktok.com"]):
        media_type = MediaType.VIDEO
        if "/photo/" in clean_url:
            media_type = MediaType.CAROUSEL
        return {
            "platform": Platform.TIKTOK,
            "name": "TikTok",
            "media_type": media_type,
            "url": clean_url
        }

    # 5. Instagram
    if "instagram.com" in clean_url or "instagr.am" in clean_url:
        media_type = MediaType.CAROUSEL
        if "/reel/" in clean_url or "/reels/" in clean_url:
            media_type = MediaType.VIDEO
        elif "/stories/" in clean_url:
            media_type = MediaType.CAROUSEL
        return {
            "platform": Platform.INSTAGRAM,
            "name": "Instagram",
            "media_type": media_type,
            "url": clean_url
        }

    # 6. Threads
    if any(domain in clean_url for domain in ["threads.net", "threads.com"]):
        return {
            "platform": Platform.THREADS,
            "name": "Threads",
            "media_type": MediaType.CAROUSEL,
            "url": clean_url
        }

    # 7. Twitter / X
    if any(domain in clean_url for domain in ["twitter.com", "x.com"]):
        return {
            "platform": Platform.TWITTER,
            "name": "Twitter / X",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 8. SoundCloud
    if "soundcloud.com" in clean_url:
        return {
            "platform": Platform.SOUNDCLOUD,
            "name": "SoundCloud",
            "media_type": MediaType.AUDIO,
            "url": clean_url
        }

    # 9. Pinterest
    if any(domain in clean_url for domain in ["pinterest.com", "pin.it"]):
        return {
            "platform": Platform.PINTEREST,
            "name": "Pinterest",
            "media_type": MediaType.IMAGE,
            "url": clean_url
        }

    # 10. Facebook
    if any(domain in clean_url for domain in ["facebook.com", "fb.watch", "fb.com"]):
        return {
            "platform": Platform.FACEBOOK,
            "name": "Facebook",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 11. Reddit
    if any(domain in clean_url for domain in ["reddit.com", "redd.it"]):
        return {
            "platform": Platform.REDDIT,
            "name": "Reddit",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 12. Bilibili
    if any(domain in clean_url for domain in ["bilibili.com", "bilibili.tv", "b23.tv"]):
        return {
            "platform": Platform.BILIBILI,
            "name": "Bilibili",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 13. Vimeo
    if "vimeo.com" in clean_url:
        return {
            "platform": Platform.VIMEO,
            "name": "Vimeo",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 14. Dailymotion
    if any(domain in clean_url for domain in ["dailymotion.com", "dai.ly"]):
        return {
            "platform": Platform.DAILYMOTION,
            "name": "Dailymotion",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 15. Twitch
    if "twitch.tv" in clean_url:
        return {
            "platform": Platform.TWITCH,
            "name": "Twitch",
            "media_type": MediaType.VIDEO,
            "url": clean_url
        }

    # 16. Generic (Fallback ke yt-dlp)
    return {
        "platform": Platform.GENERIC,
        "name": "Universal / Web",
        "media_type": MediaType.UNKNOWN,
        "url": clean_url
    }
