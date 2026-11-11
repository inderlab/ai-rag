import pytest

from app.ingestion.youtube import extract_video_id, fmt_ts

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&t=42s",
        f"https://m.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}",
        f"https://youtu.be/{VID}?si=abc123",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"youtube.com/watch?v={VID}",
        VID,
    ],
)
def test_extract_video_id_valid(url):
    assert extract_video_id(url) == VID


@pytest.mark.parametrize(
    "url",
    ["", "https://vimeo.com/123456", "https://www.youtube.com/watch?v=short", "hello world"],
)
def test_extract_video_id_invalid(url):
    assert extract_video_id(url) is None


@pytest.mark.parametrize("sec,expected", [(0, "00:00"), (65, "01:05"), (3725.9, "1:02:05")])
def test_fmt_ts(sec, expected):
    assert fmt_ts(sec) == expected
