import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str | None:
    """Get the 11-char video id from watch, youtu.be, shorts, embed or live links."""
    url = url.strip()
    if VIDEO_ID_RE.match(url):
        return url

    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")

    candidate = None
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]

    return candidate if candidate and VIDEO_ID_RE.match(candidate) else None


def fetch_transcript(video_id: str, languages: tuple[str, ...] = ("en", "hi")) -> list[dict]:
    """Return caption segments as [{text, start, end}] (seconds)."""
    fetched = YouTubeTranscriptApi().fetch(video_id, languages=list(languages))
    return [
        {"text": s.text, "start": round(s.start, 2), "end": round(s.start + s.duration, 2)}
        for s in fetched
    ]


def fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
