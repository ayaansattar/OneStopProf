import base64
import json
import re
import time
from datetime import datetime, timedelta, timezone
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

LIST_TEACHERS_QUERY = """
query ListTeachersQuery($query: TeacherSearchQuery!, $first: Int!, $after: String) {
  newSearch {
    teachers(query: $query, first: $first, after: $after) {
      edges {
        cursor
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
      pageInfo {
        hasNextPage
        endCursor
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


def parse_rmp_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        cleaned = date_str.replace(" +0000 UTC", "+0000")
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S%z")
    except ValueError:
        return None


def review_cutoff(max_age_years: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max_age_years * 365)


def has_recent_review(teacher_id: str, max_age_years: int = 5) -> bool:
    """True if the professor's most recent review is within max_age_years."""
    raw = get_professor_reviews(teacher_id, count=1)
    if not raw:
        return False
    review_date = parse_rmp_date(raw[0].get("date", ""))
    if not review_date:
        return False
    return review_date >= review_cutoff(max_age_years)


def filter_raw_reviews_by_age(raw_reviews: list[dict], max_age_years: int) -> list[dict]:
    cutoff = review_cutoff(max_age_years)
    filtered = []
    for review in raw_reviews:
        review_date = parse_rmp_date(review.get("date", ""))
        if review_date and review_date >= cutoff:
            filtered.append(review)
    return filtered


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def list_professors_at_school(
    school_id: str,
    page_size: int = 20,
    limit: int | None = None,
) -> list[dict]:
    """Return professors at a school (paginated GraphQL search with empty text)."""
    if not school_id.startswith("U"):
        school_id = encode_rmp_id("School", school_id)

    professors: list[dict] = []
    after = None

    while True:
        variables = {
            "query": {"schoolID": school_id, "text": ""},
            "first": page_size,
            "after": after,
        }
        data = _post(LIST_TEACHERS_QUERY, variables)
        teachers = data["data"]["newSearch"]["teachers"]
        edges = teachers["edges"]
        professors.extend(edge["node"] for edge in edges)

        if limit and len(professors) >= limit:
            return professors[:limit]

        page_info = teachers["pageInfo"]
        if not page_info.get("hasNextPage"):
            break
        after = page_info["endCursor"]
        time.sleep(0.5)

    return professors


def teacher_to_meta(teacher: dict, university: str) -> dict:
    full_name = f"{teacher['firstName']} {teacher['lastName']}".strip()
    return {
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


def scrape_school(
    school_id: str,
    university: str,
    review_count: int = 100,
    min_ratings: int = 5,
    max_review_age_years: int = 5,
    limit: int | None = None,
    delay: float = 1.0,
    output_reviews: str | Path = "data/rmp_reviews.json",
    output_professors: str | Path = "data/professors.json",
    checkpoint_path: str | Path = "data/scrape_checkpoint.json",
    resume: bool = True,
) -> dict:
    """
    Scrape reviews for professors at a school.

    Filters:
    - numRatings > min_ratings (default: more than 5 reviews)
    - most recent review within max_review_age_years (default: 5 years)
    - only reviews within max_review_age_years are saved
    """
    reviews_path = Path(output_reviews)
    professors_path = Path(output_professors)
    checkpoint_file = Path(checkpoint_path)
    reviews_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching professor list for {university} (school {school_id})...")
    all_teachers = list_professors_at_school(school_id, limit=limit)
    all_teachers = [t for t in all_teachers if (t.get("numRatings") or 0) > min_ratings]

    eligible_teachers = []
    print(f"Checking recency for {len(all_teachers)} professors (> {min_ratings} ratings)...")
    for i, teacher in enumerate(all_teachers, 1):
        name = f"{teacher['firstName']} {teacher['lastName']}".strip()
        if has_recent_review(teacher["id"], max_review_age_years):
            eligible_teachers.append(teacher)
            print(f"  [{i}/{len(all_teachers)}] {name} — recent activity")
        else:
            print(f"  [{i}/{len(all_teachers)}] {name} — skipped (no review in last {max_review_age_years}y)")
        time.sleep(delay * 0.3)

    with professors_path.open("w", encoding="utf-8") as f:
        json.dump([teacher_to_meta(t, university) for t in eligible_teachers], f, indent=2)
    print(
        f"\n{len(eligible_teachers)} professors eligible "
        f"(> {min_ratings} ratings, review within {max_review_age_years} years)"
    )

    start_index = 0
    all_reviews: list[dict] = []
    if resume and reviews_path.exists():
        with reviews_path.open(encoding="utf-8") as f:
            all_reviews = json.load(f)
    if resume and checkpoint_file.exists():
        with checkpoint_file.open(encoding="utf-8") as f:
            checkpoint = json.load(f)
        start_index = checkpoint.get("next_index", 0)
        print(f"Resuming from professor {start_index + 1}/{len(eligible_teachers)}")
    elif not resume:
        if reviews_path.exists():
            reviews_path.unlink()
        if checkpoint_file.exists():
            checkpoint_file.unlink()

    stats = {"scraped": 0, "skipped": 0, "reviews": len(all_reviews), "errors": 0}

    for i, teacher in enumerate(eligible_teachers[start_index:], start=start_index):
        meta = teacher_to_meta(teacher, university)
        name = meta["name"]
        num_ratings = teacher.get("numRatings") or 0
        print(f"[{i + 1}/{len(eligible_teachers)}] {name} ({num_ratings} ratings)...", end=" ")

        try:
            count = min(review_count, num_ratings) if num_ratings else review_count
            raw_reviews = get_professor_reviews(teacher["id"], count=count)
            raw_reviews = filter_raw_reviews_by_age(raw_reviews, max_review_age_years)
            reviews = normalize_reviews(raw_reviews, meta)
            if not reviews:
                stats["skipped"] += 1
                print("skipped (no recent reviews)")
                continue

            all_reviews.extend(reviews)
            stats["scraped"] += 1
            stats["reviews"] += len(reviews)
            print(f"{len(reviews)} reviews")

            with reviews_path.open("w", encoding="utf-8") as f:
                json.dump(all_reviews, f, ensure_ascii=False)
            with checkpoint_file.open("w", encoding="utf-8") as f:
                json.dump({"next_index": i + 1, "total": len(eligible_teachers)}, f)

        except Exception as exc:
            stats["errors"] += 1
            print(f"ERROR: {exc}")

        time.sleep(delay)

    if checkpoint_file.exists() and start_index + stats["scraped"] + stats["skipped"] + stats["errors"] >= len(eligible_teachers):
        checkpoint_file.unlink(missing_ok=True)

    print(
        f"\nDone. Professors scraped: {stats['scraped']}, "
        f"skipped: {stats['skipped']}, errors: {stats['errors']}, "
        f"total reviews: {stats['reviews']}"
    )
    print(f"Reviews saved to {reviews_path}")
    print(f"Professor list saved to {professors_path}")
    return stats


def normalize_reviews(    raw_reviews: list[dict],
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

    professor_meta = teacher_to_meta(teacher, university)
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
