import sys
from pathlib import Path

import pytest

from app.config import settings
from app.ingestion import embedder
from app.vectorstore import chroma_store
from tests.fakes import FakeModel

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(autouse=True)
def isolated_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUTO_INSIGHTS", False)
    embedder.set_model(FakeModel())
    chroma_store.set_store(chroma_store.ChromaStore(str(tmp_path / "chroma"), "test_chunks"))
    yield
    chroma_store.set_store(None)
    embedder.set_model(None)
