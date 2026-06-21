import json
from pathlib import Path

from pipeline.chunker import chunk_all_reviews
from pipeline.embedder import embed_texts
from pipeline.loader import get_collection, load_chunks


def run(source_file: str | Path) -> dict:
    path = Path(source_file)
    with path.open(encoding="utf-8") as f:
        reviews = json.load(f)

    chunks = chunk_all_reviews(reviews)
    print(f"Created {len(chunks)} chunks from {len(reviews)} reviews")

    loaded = load_chunks(chunks)
    return {
        "reviews": len(reviews),
        "chunks": len(chunks),
        "loaded": loaded,
    }


def verify_retrieval(query: str, professor_id: str, n_results: int = 3) -> list[dict]:
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
                "course": meta.get("course", ""),
                "rating": meta.get("rating", ""),
                "distance": dist,
            }
        )
    return matches


if __name__ == "__main__":
    stats = run("data/rmp_reviews.json")
    print(f"Pipeline complete: {stats}")

    professor_id = "umass_amherst_marius_minea"
    test_query = "Is this professor good for beginners in programming?"
    print(f"\nTest query: {test_query}")
    matches = verify_retrieval(test_query, professor_id)
    for i, match in enumerate(matches, 1):
        print(f"\n[{i}] course={match['course']} rating={match['rating']} distance={match['distance']:.4f}")
        print(match["text"][:200] + ("..." if len(match["text"]) > 200 else ""))
