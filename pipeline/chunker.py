CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
SEPARATORS = ("\n\n", "\n", ". ", " ")


def split_text(
    text: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: tuple[str, ...] = SEPARATORS,
) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separator = separators[-1]
    for candidate in separators:
        if candidate in text:
            separator = candidate
            break

    if separator == separators[-1]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start = max(end - chunk_overlap, start + 1)
        return chunks

    parts = text.split(separator)
    next_separators = separators[separators.index(separator) + 1 :]
    chunks: list[str] = []
    current = ""

    for index, part in enumerate(parts):
        segment = part if index == len(parts) - 1 else part + separator
        if len(segment) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.extend(
                split_text(
                    segment,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=next_separators or (separators[-1],),
                )
            )
            continue

        combined = current + segment
        if len(combined) <= chunk_size:
            current = combined
        else:
            if current.strip():
                chunks.append(current.strip())
            current = segment

    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_review(review: dict) -> list[dict]:
    text = review["review_text"]
    if len(text.split()) < 150:
        return [{**review, "chunk_id": 0}]
    chunks = split_text(text)
    return [
        {**review, "review_text": chunk, "chunk_id": i}
        for i, chunk in enumerate(chunks)
    ]


def chunk_all_reviews(reviews: list[dict]) -> list[dict]:
    all_chunks = []
    for review_index, review in enumerate(reviews):
        for chunk in chunk_review(review):
            chunk["review_index"] = review_index
            all_chunks.append(chunk)
    return all_chunks
