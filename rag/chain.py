import os
from collections import defaultdict

from dotenv import load_dotenv
from groq import Groq

from rag.retriever import extract_course_code, retrieve, retrieve_for_recommendation

load_dotenv()

_client = None

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about university professors
based on real student reviews. Follow these rules:
- Always cite which source each claim comes from (Rate My Professor)
- Be balanced and acknowledge both positive and negative reviews
- If reviews conflict, present both perspectives
- Never fabricate or infer information not present in the reviews
- Keep answers concise (2-4 paragraphs max)
"""

RECOMMEND_PROMPT = """You help students choose professors for a course using real Rate My Professor reviews.
Follow these rules:
- Recommend 2–4 professors when evidence supports it, ranked best-fit first
- Match the student's constraints (beginner-friendly, grading, exams, workload, difficulty)
- Always name the professor and course when citing a claim
- Cite Rate My Professor; never invent reviews or ratings
- If evidence is thin, conflicting, or not clearly about the target course, say so
- Keep the answer concise (about 2–4 short paragraphs or a short ranked list with reasons)
"""


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            try:
                import streamlit as st

                api_key = st.secrets.get("GROQ_API_KEY")
            except Exception:
                api_key = None
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env or Streamlit secrets")
        _client = Groq(api_key=api_key)
    return _client


def _format_context(chunks: list[dict]) -> str:
    parts = []
    for chunk in chunks:
        course = f" ({chunk['course']})" if chunk.get("course") else ""
        name = chunk.get("name") or "Unknown professor"
        parts.append(f"[{name} | {chunk['source'].upper()}{course}] {chunk['text']}")
    return "\n---\n".join(parts)


def _format_recommendation_context(chunks: list[dict], max_per_professor: int = 3) -> str:
    by_prof: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        pid = chunk.get("professor_id") or chunk.get("name") or "unknown"
        by_prof[pid].append(chunk)

    sections = []
    for pid, prof_chunks in by_prof.items():
        prof_chunks = sorted(prof_chunks, key=lambda c: c.get("distance", 1.0))
        top = prof_chunks[:max_per_professor]
        name = top[0].get("name") or pid
        dept = top[0].get("department") or ""
        header = f"### {name}" + (f" ({dept})" if dept else "")
        body = _format_context(top)
        sections.append(f"{header}\n{body}")
    return "\n\n".join(sections)


def _professor_summaries(chunks: list[dict]) -> list[dict]:
    by_prof: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        pid = chunk.get("professor_id")
        if not pid:
            continue
        by_prof[pid].append(chunk)

    summaries = []
    for pid, prof_chunks in by_prof.items():
        ratings = []
        for chunk in prof_chunks:
            raw = chunk.get("rating")
            if raw in (None, ""):
                continue
            try:
                ratings.append(float(raw))
            except (TypeError, ValueError):
                pass
        summaries.append(
            {
                "id": pid,
                "name": prof_chunks[0].get("name") or pid,
                "avg_rating_in_context": (
                    sum(ratings) / len(ratings) if ratings else None
                ),
                "review_count_in_context": len(prof_chunks),
            }
        )

    summaries.sort(
        key=lambda s: (
            -(s["avg_rating_in_context"] or 0),
            -s["review_count_in_context"],
        )
    )
    return summaries


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


def recommend(query: str, n_results: int = 24) -> dict:
    course = extract_course_code(query)
    chunks = retrieve_for_recommendation(query, course=course, n_results=n_results)

    if not chunks:
        return {
            "answer": "No relevant professor reviews found for that question.",
            "sources": [],
            "course": course,
            "professors": [],
        }

    professors = _professor_summaries(chunks)
    context = _format_recommendation_context(chunks)
    course_note = (
        f"Detected course filter: {course}."
        if course
        else "No course code detected; using open semantic search across professors."
    )
    messages = [
        {"role": "system", "content": RECOMMEND_PROMPT},
        {
            "role": "user",
            "content": (
                f"{course_note}\n\n"
                f"Student reviews by professor:\n{context}\n\n"
                f"Student question: {query}\n\n"
                "Recommend professors and explain why, using only the reviews above."
            ),
        },
    ]

    client = get_client()
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=900,
        temperature=0.3,
    )

    return {
        "answer": resp.choices[0].message.content,
        "sources": chunks,
        "course": course,
        "professors": professors,
    }


if __name__ == "__main__":
    print("=== Recommend mode ===")
    rec = recommend("Who should I take for CS220 as a beginner?")
    print(f"Course: {rec['course']}")
    print(rec["answer"])
    print(f"({len(rec['sources'])} sources, {len(rec['professors'])} professors)")

    print("\n=== Ask mode ===")
    professor_id = "umass_amherst_marius_minea"
    result = ask("How difficult is his grading?", professor_id)
    print(result["answer"])
    print(f"\n({len(result['sources'])} source reviews used)")
