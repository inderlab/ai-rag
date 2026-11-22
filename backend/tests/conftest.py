import pytest

from app.ingestion import embedder
from app.vectorstore import chroma_store
from tests.fakes import FakeModel


@pytest.fixture(autouse=True)
def isolated_ai(tmp_path):
    embedder.set_model(FakeModel())
    chroma_store.set_store(chroma_store.ChromaStore(str(tmp_path / "chroma"), "test_chunks"))
    yield
    chroma_store.set_store(None)
    embedder.set_model(None)
