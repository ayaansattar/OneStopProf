from pipeline.embedder import embed_texts
from pipeline.loader import get_collection


def retrieve(query: str, professor_id: str, n_results: int = 6) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"professor_id": professor_id},
        include=["documents", "metadatas", "distances"],
    )

    matches = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        matches.append(
            {
                "text": doc,
                "source": meta.get("source", "unknown"),
                "course": meta.get("course", ""),
                "rating": meta.get("rating"),
                "date": meta.get("date"),
                "distance": dist,
            }
        )
    return matches
