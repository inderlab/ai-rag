import hashlib
import math

DIM = 64


class FakeModel:
    name = "fake-bow"
    dimension = DIM

    def __init__(self):
        self.encoded: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.encoded.extend(texts)
        out = []
        for text in texts:
            vec = [0.0] * DIM
            for word in text.lower().split()[1:]:
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out
