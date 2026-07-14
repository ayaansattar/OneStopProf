import sys

try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb

from pipeline.embedder import embed_texts

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "professor_reviews"

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_id(chunk: dict) -> str:
    return (
        f"{chunk['professor_id']}_{chunk['source']}_"
        f"{chunk['review_index']}_{chunk['chunk_id']}"
    )


def _metadata(chunk: dict) -> dict:
    meta = {}
    for key, value in chunk.items():
        if key == "review_text":
            continue
        if value is None:
            meta[key] = ""
        elif isinstance(value, list):
            meta[key] = ", ".join(str(item) for item in value)
        else:
            meta[key] = value
    return meta


BATCH_SIZE = 5000


def load_chunks(chunks: list[dict]) -> int:
    if not chunks:
        print("No chunks to load.")
        return 0

    collection = get_collection()
    texts = [c["review_text"] for c in chunks]
    embeddings = embed_texts(texts)

    for start in range(0, len(chunks), BATCH_SIZE):
        end = start + BATCH_SIZE
        batch = chunks[start:end]
        collection.upsert(
            ids=[_chunk_id(c) for c in batch],
            documents=texts[start:end],
            embeddings=embeddings[start:end],
            metadatas=[_metadata(c) for c in batch],
        )
        print(f"Loaded batch {start // BATCH_SIZE + 1}: {len(batch)} chunks")

    print(f"Loaded {len(chunks)} chunks into ChromaDB")
    return len(chunks)
