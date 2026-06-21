import os

from dotenv import load_dotenv
from groq import Groq

from rag.retriever import retrieve

load_dotenv()

_client = None

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about university professors
based on real student reviews. Follow these rules:
- Always cite which source each claim comes from (Rate My Professor or Reddit)
- Be balanced and acknowledge both positive and negative reviews
- If reviews conflict, present both perspectives
- Never fabricate or infer information not present in the reviews
- Keep answers concise (2-4 paragraphs max)
"""


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        _client = Groq(api_key=api_key)
    return _client


def _format_context(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks:
        course = f" ({chunk['course']})" if chunk.get("course") else ""
        parts.append(f"[{chunk['source'].upper()}{course}] {chunk['text']}")
    return "\n---\n".join(parts)


def ask(query: str, professor_id: str, n_results: int = 6) -> dict:
    chunks = retrieve(query, professor_id, n_results=n_results)

    if not chunks:
        return {"answer": "No reviews found for this professor.", "sources": []}

    context = _format_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Student reviews:\n{context}\n\nQuestion: {query}",
        },
    ]

    client = get_client()
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=800,
        temperature=0.3,
    )

    return {
        "answer": resp.choices[0].message.content,
        "sources": chunks,
    }


if __name__ == "__main__":
    professor_id = "umass_amherst_marius_minea"
    test_queries = [
        "Is Marius Minea good for beginners in CS220?",
        "How difficult is his grading?",
        "What do students say about his teaching style?",
    ]

    for query in test_queries:
        print(f"\n{'=' * 60}")
        print(f"Q: {query}")
        print("=" * 60)
        result = ask(query, professor_id)
        print(result["answer"])
        print(f"\n({len(result['sources'])} source reviews used)")
