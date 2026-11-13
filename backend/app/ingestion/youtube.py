import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str | None:
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


DEFAULT_LANGUAGES = ("en", "en-IN", "hi")

FRIENDLY_ERRORS: dict[type[Exception], str] = {
    TranscriptsDisabled: "Captions are turned off for this video",
    NoTranscriptFound: "This video has no captions",
    VideoUnavailable: "Video is private, deleted or unavailable",
    VideoUnplayable: "Video cannot be played (region or members-only)",
    AgeRestricted: "Video is age-restricted",
    InvalidVideoId: "Not a valid YouTube video id",
    RequestBlocked: "YouTube blocked the request from this network",
    IpBlocked: "YouTube blocked the request from this network",
}


@dataclass
class Captions:
    segments: list[dict]
    language: str
    is_generated: bool


def fetch_captions(video_id: str, languages: tuple[str, ...] = DEFAULT_LANGUAGES) -> Captions:
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=list(languages))
    except NoTranscriptFound:
        available = list(api.list(video_id))
        if not available:
            raise
        fetched = available[0].fetch()
    segments = [
        {
            "text": " ".join(s.text.split()),
            "start": round(s.start, 2),
            "end": round(s.start + s.duration, 2),
        }
        for s in fetched
        if s.text.strip()
    ]
    return Captions(
        segments=segments, language=fetched.language_code, is_generated=fetched.is_generated
    )


def fetch_transcript(video_id: str, languages: tuple[str, ...] = DEFAULT_LANGUAGES) -> list[dict]:
    return fetch_captions(video_id, languages).segments


def fetch_metadata(video_id: str) -> dict:
    r = httpx.get(
        "https://www.youtube.com/oembed",
        params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return {"title": data.get("title"), "channel": data.get("author_name")}


def friendly_error(e: Exception) -> str:
    for cls, message in FRIENDLY_ERRORS.items():
        if isinstance(e, cls):
            return message
    first_line = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
    return first_line[:300]


def fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
