import sys

sys.path.insert(0, "backend")

URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ?t=42",
    "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    "https://vimeo.com/123456",
]


def main(url: str | None) -> None:
    from app.ingestion.youtube import (
        extract_video_id,
        fetch_captions,
        fetch_metadata,
        fmt_ts,
        friendly_error,
    )
    from youtube_transcript_api import YouTubeTranscriptApiException

    print("=== 1. Video ID from different link formats ===")
    for u in URLS:
        print(f"{u:50} -> {extract_video_id(u)}")

    video_id = extract_video_id(url or URLS[0])
    if not video_id:
        sys.exit("Not a YouTube link")

    print(f"\n=== 2. Captions for {video_id} ===")
    try:
        captions = fetch_captions(video_id)
    except YouTubeTranscriptApiException as e:
        sys.exit(f"Failed: {friendly_error(e)}")

    meta = fetch_metadata(video_id)
    kind = "auto-generated" if captions.is_generated else "human-written"
    print(f"Title    : {meta['title']}")
    print(f"Channel  : {meta['channel']}")
    print(f"Language : {captions.language} ({kind})")
    print(f"Segments : {len(captions.segments)}")
    print(f"Duration : {fmt_ts(captions.segments[-1]['end'])}\n")

    for seg in captions.segments[:10]:
        print(f"[{fmt_ts(seg['start'])}] {seg['text']}")

    words = sum(len(s["text"].split()) for s in captions.segments)
    print(f"\nTotal words: {words}  (about {int(words * 1.3)} tokens)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
