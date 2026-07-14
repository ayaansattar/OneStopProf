from __future__ import annotations

import re

from pipeline.embedder import embed_texts
from pipeline.loader import get_collection

MIN_COURSE_HITS = 6

# Common UMass department aliases so CS220 also matches COMPSCI220, etc.
PREFIX_ALIASES: dict[str, list[str]] = {
    "CS": ["CS", "COMPSCI", "CICS"],
    "COMPSCI": ["CS", "COMPSCI", "CICS"],
    "CICS": ["CS", "COMPSCI", "CICS"],
    "CHEM": ["CHEM", "CHEMISTRY"],
    "CHEMISTRY": ["CHEM", "CHEMISTRY"],
    "BIO": ["BIO", "BIOLOGY", "BIOL"],
    "BIOLOGY": ["BIO", "BIOLOGY", "BIOL"],
    "BIOL": ["BIO", "BIOLOGY", "BIOL"],
    "MATH": ["MATH", "CALC"],
    "CALC": ["MATH", "CALC"],
    "STAT": ["STAT", "STATS", "STATISTICS"],
    "STATS": ["STAT", "STATS", "STATISTICS"],
    "ENG": ["ENG", "ENGL", "ENGLISH"],
    "ENGL": ["ENG", "ENGL", "ENGLISH", "ENGLWRIT"],
    "ENGLWRIT": ["ENGLWRIT", "ENGL", "ENG"],
    "PHYS": ["PHYS", "PHYSICS"],
    "PHYSICS": ["PHYS", "PHYSICS"],
    "ECON": ["ECON", "ECONOMICS"],
    "KIN": ["KIN", "KINESIOLOGY"],
    "ASTRON": ["ASTRON", "ASTRONOMY", "ASTRO"],
    "GEO": ["GEO", "GEOG", "GEOLOGY", "GEOSCI"],
}


def normalize_course_token(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", text).upper()


def extract_course_code(query: str) -> str | None:
    """Pull a course code like CS220, CHEM 111, or ENGLWRIT112 from free text."""
    match = re.search(
        r"\b([A-Za-z]{2,10})\s?-?\s?(\d{2,4}[A-Za-z]?)\b",
        query,
    )
    if not match:
        return None
    prefix, number = match.group(1), match.group(2)
    return f"{prefix.upper()}{number.upper()}"


def course_filter_candidates(course: str) -> list[str]:
    """Build metadata values that may appear in scraped RMP course fields."""
    normalized = normalize_course_token(course)
    prefix_match = re.match(r"^([A-Z]+)(\d+[A-Z]?)$", normalized)
    if not prefix_match:
        return [course, normalized]

    prefix, number = prefix_match.group(1), prefix_match.group(2)
    prefixes = PREFIX_ALIASES.get(prefix, [prefix])
    candidates: set[str] = set()
    for p in prefixes:
        candidates.add(f"{p}{number}")
        candidates.add(f"{p}-{number}")
        candidates.add(f"{p} {number}")
        candidates.add(f"{p.lower()}{number}")
        candidates.add(f"{p.lower()}-{number}")
        # Title-style: Biology-151
        if len(p) > 3:
            title = p[:1] + p[1:].lower()
            candidates.add(f"{title}-{number}")
            candidates.add(f"{title}{number}")
    candidates.add(normalized)
    candidates.add(course)
    return sorted(candidates)


def _matches_from_results(results: dict) -> list[dict]:
    if not results.get("documents") or not results["documents"][0]:
        return []

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
                "professor_id": meta.get("professor_id", ""),
                "name": meta.get("name", ""),
                "department": meta.get("department", ""),
                "university": meta.get("university", ""),
            }
        )
    return matches


def retrieve(query: str, professor_id: str, n_results: int = 6) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"professor_id": professor_id},
        include=["documents", "metadatas", "distances"],
    )
    return _matches_from_results(results)


def retrieve_for_recommendation(
    query: str,
    course: str | None = None,
    n_results: int = 24,
    min_hits: int = MIN_COURSE_HITS,
) -> list[dict]:
    """Semantic search across professors, optionally filtered by course metadata."""
    collection = get_collection()
    query_embedding = embed_texts([query])[0]

    matches: list[dict] = []
    if course:
        candidates = course_filter_candidates(course)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"course": {"$in": candidates}},
                include=["documents", "metadatas", "distances"],
            )
            matches = _matches_from_results(results)
        except Exception:
            matches = []

    if len(matches) < min_hits:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        open_matches = _matches_from_results(results)
        if not matches:
            return open_matches

        # Prefer course-filtered hits, then fill with open search (dedupe by text+prof)
        seen = {(m["professor_id"], m["text"][:80]) for m in matches}
        for match in open_matches:
            key = (match["professor_id"], match["text"][:80])
            if key in seen:
                continue
            matches.append(match)
            seen.add(key)
            if len(matches) >= n_results:
                break

    return matches[:n_results]
