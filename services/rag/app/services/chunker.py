from common.config import conf


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    size = conf.CHILD_CHUNK_SIZE
    overlap = conf.CHUNK_OVERLAP
    if size <= 0:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks
