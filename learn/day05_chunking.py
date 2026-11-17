import sys

sys.path.insert(0, "backend")

VIDEO = "dQw4w9WgXcQ"
SIZES = [100, 300, 800]
OVERLAP = 50


def main(video: str) -> None:
    from app.ingestion.chunker import chunk_segments, chunk_words, shared_segments, stats
    from app.ingestion.youtube import extract_video_id, fetch_captions, fmt_ts, friendly_error
    from youtube_transcript_api import YouTubeTranscriptApiException

    print("=== 1. Overlap on plain text (max 6 words, overlap 2) ===")
    text = "pehle dependency add karo phir properties mein URL likho phir entity banao aur run karo"
    for i, part in enumerate(chunk_words(text, max_words=6, overlap_words=2)):
        print(f"chunk {i}: {part}")

    video_id = extract_video_id(video) or video
    try:
        captions = fetch_captions(video_id)
    except YouTubeTranscriptApiException as e:
        sys.exit(f"Failed: {friendly_error(e)}")
    segments = captions.segments
    total = sum(len(s["text"].split()) for s in segments)
    print(f"\n=== 2. Video {video_id}: {len(segments)} segments, {total} words ===")
    print(f"{'size':>5} {'overlap':>7} {'chunks':>6} {'avg words':>9}  first chunk")
    for size in SIZES:
        overlap = min(OVERLAP, size // 5)
        chunks = chunk_segments(segments, size, overlap)
        s = stats(chunks)
        first = f"{fmt_ts(chunks[0].start)} - {fmt_ts(chunks[0].end)}" if chunks else "-"
        print(f"{size:>5} {overlap:>7} {s['count']:>6} {s['avg_words']:>9}  {first}")

    small = chunk_segments(segments, 60, 15)
    if len(small) > 1:
        a, b = small[0], small[1]
        print("\n=== 3. Where two chunks overlap (size 60, overlap 15) ===")
        print(f"chunk 0 ends   : ...{a.text[-80:]}")
        print(f"chunk 1 starts : {b.text[:80]}...")
        print(f"shared segments: {shared_segments(a, b)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else VIDEO)
