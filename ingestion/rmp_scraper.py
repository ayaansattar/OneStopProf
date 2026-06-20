import base64
import json
import re
from pathlib import Path

import httpx

RMP_GRAPHQL = "https://www.ratemyprofessors.com/graphql"
RMP_HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://www.ratemyprofessors.com",
    "Referer": "https://www.ratemyprofessors.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}

SEARCH_QUERY = """
query TeacherSearchResultsPageQuery($query: TeacherSearchQuery!) {
  search: newSearch {
    teachers(query: $query, first: 8) {
      edges {
        node {
          id
          firstName
          lastName
          avgRating
          avgDifficulty
          wouldTakeAgainPercent
          numRatings
          department
        }
      }
    }
  }
}
"""

RATINGS_QUERY = """
query RatingsListQuery($id: ID!, $count: Int!) {
  node(id: $id) {
    ... on Teacher {
      ratings(first: $count) {
        edges {
          node {
            comment
            qualityRating
            difficultyRatingRounded
            wouldTakeAgain
            ratingTags
            date
            class
            helpfulRating
            clarityRating
          }
        }
      }
    }
  }
}
"""


def _post(query: str, variables: dict) -> dict:
    resp = httpx.post(
        RMP_GRAPHQL,
        json={"query": query, "variables": variables},
        headers=RMP_HEADERS,
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"RMP GraphQL error: {data['errors']}")
    return data


def encode_rmp_id(entity_type: str, numeric_id: str | int) -> str:
    raw = f"{entity_type}-{numeric_id}"
    return base64.b64encode(raw.encode()).decode()


def decode_rmp_id(encoded_id: str) -> str:
    return base64.b64decode(encoded_id).decode()


def search_professor(name: str, school_id: str) -> list[dict]:
    if not school_id.startswith("U"):
        school_id = encode_rmp_id("School", school_id)
    variables = {"query": {"text": name, "schoolID": str(school_id)}}
    data = _post(SEARCH_QUERY, variables)
    edges = data["data"]["search"]["teachers"]["edges"]
    return [edge["node"] for edge in edges]


def get_professor_reviews(teacher_id: str, count: int = 100) -> list[dict]:
    variables = {"id": teacher_id, "count": count}
    data = _post(RATINGS_QUERY, variables)
    node = data["data"]["node"]
    if not node:
        return []
    edges = node["ratings"]["edges"]
    return [edge["node"] for edge in edges]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_reviews(
    raw_reviews: list[dict],
    professor_meta: dict,
) -> list[dict]:
    normalized = []
    for review in raw_reviews:
        comment = (review.get("comment") or "").strip()
        if not comment:
            continue

        tags = review.get("ratingTags") or []
        if isinstance(tags, list):
            tag_names = [
                t.get("tagName", t) if isinstance(t, dict) else str(t)
                for t in tags
            ]
        else:
            tag_names = []

        would_retake = review.get("wouldTakeAgain")
        if would_retake is not None:
            would_retake = would_retake == "YES"

        normalized.append(
            {
                "professor_id": professor_meta["professor_id"],
                "name": professor_meta["name"],
                "university": professor_meta["university"],
                "department": professor_meta.get("department", ""),
                "course": review.get("class") or "",
                "source": "ratemyprofessor",
                "rating": review.get("qualityRating"),
                "difficulty": review.get("difficultyRatingRounded"),
                "would_retake": would_retake,
                "tags": tag_names,
                "review_text": comment,
                "date": review.get("date") or "",
                "upvotes": review.get("helpfulRating") or 0,
            }
        )
    return normalized


def scrape_professor(
    name: str,
    school_id: str,
    university: str,
    review_count: int = 100,
    teacher_numeric_id: str | int | None = None,
) -> tuple[dict, list[dict]]:
    matches = search_professor(name, school_id)
    if not matches:
        raise ValueError(f"No professors found for '{name}' at school {school_id}")

    if teacher_numeric_id:
        target_id = encode_rmp_id("Teacher", teacher_numeric_id)
        teacher = next((m for m in matches if m["id"] == target_id), None)
        if not teacher:
            raise ValueError(
                f"Teacher {teacher_numeric_id} not found in search results for '{name}'"
            )
    else:
        teacher = matches[0]
    full_name = f"{teacher['firstName']} {teacher['lastName']}".strip()
    professor_meta = {
        "professor_id": slugify(f"{university}_{full_name}"),
        "name": full_name,
        "university": university,
        "department": teacher.get("department") or "",
        "avg_rating": teacher.get("avgRating"),
        "avg_difficulty": teacher.get("avgDifficulty"),
        "num_ratings": teacher.get("numRatings"),
        "would_take_again_percent": teacher.get("wouldTakeAgainPercent"),
        "rmp_teacher_id": teacher["id"],
    }

    raw_reviews = get_professor_reviews(teacher["id"], count=review_count)
    reviews = normalize_reviews(raw_reviews, professor_meta)
    return professor_meta, reviews


def save_reviews(reviews: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)
    return path


if __name__ == "__main__":
    meta, reviews = scrape_professor(
        name="Marius Minea",
        school_id="1513",
        university="UMass Amherst",
        review_count=100,
        teacher_numeric_id=2416008,
    )
    out = save_reviews(reviews, "data/rmp_reviews.json")
    print(f"Professor: {meta['name']} ({meta['department']})")
    print(f"Ratings on RMP: {meta['num_ratings']}")
    print(f"Saved {len(reviews)} reviews to {out}")
