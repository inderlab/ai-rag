import shutil
import subprocess
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import settings

SAMPLE_RATE = 16000


class AudioError(RuntimeError):
    pass


@dataclass
class Transcript:
    segments: list[dict]
    language: str
    duration: float


class Transcriber(Protocol):
    name: str

    def transcribe(self, path: Path) -> Transcript: ...


def ffmpeg_bin() -> str:
    found = shutil.which(settings.FFMPEG_BIN) or shutil.which("ffmpeg")
    if not found:
        for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"):
            if Path(candidate).exists():
                return candidate
        raise AudioError("FFmpeg is not installed on the server")
    return found


def load_audio(path: Path):
    import numpy as np

    cmd = [
        ffmpeg_bin(),
        "-nostdin",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-f",
        "f32le",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode(errors="ignore").strip().splitlines()
        reason = detail[-1] if detail else "no audio stream"
        raise AudioError(f"Could not read audio from the file: {reason}")
    return np.frombuffer(result.stdout, dtype=np.float32)


class WhisperTranscriber:
    def __init__(self, model: str, device: str = "cpu"):
        from faster_whisper import WhisperModel

        self.name = f"faster-whisper/{model}"
        self._model = WhisperModel(model, device=device, compute_type="int8")
        self._lock = threading.Lock()

    def transcribe(self, path: Path) -> Transcript:
        audio = load_audio(path)
        with self._lock:
            parts, info = self._model.transcribe(audio, vad_filter=True)
            segments = [
                {
                    "text": " ".join(p.text.split()),
                    "start": round(p.start, 2),
                    "end": round(p.end, 2),
                }
                for p in parts
                if p.text.strip()
            ]
        return Transcript(segments=segments, language=info.language, duration=info.duration)


_override: Transcriber | None = None
_init_lock = threading.Lock()


@lru_cache
def _default() -> Transcriber:
    return WhisperTranscriber(settings.WHISPER_MODEL, settings.WHISPER_DEVICE)


def get_transcriber() -> Transcriber:
    if _override is not None:
        return _override
    with _init_lock:
        return _default()


def set_transcriber(transcriber: Transcriber | None) -> None:
    global _override
    _override = transcriber
