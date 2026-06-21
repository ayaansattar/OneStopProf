from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " "],
)


def chunk_review(review: dict) -> list[dict]:
    text = review["review_text"]
    if len(text.split()) < 150:
        return [{**review, "chunk_id": 0}]
    chunks = splitter.split_text(text)
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
