"""Scrape all professors at a school from Rate My Professors."""

import argparse

from ingestion.rmp_scraper import scrape_school

UMASS_AMHERST = {
    "school_id": "1513",
    "university": "UMass Amherst",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape RMP reviews for an entire school")
    parser.add_argument("--school-id", default=UMASS_AMHERST["school_id"])
    parser.add_argument("--university", default=UMASS_AMHERST["university"])
    parser.add_argument("--review-count", type=int, default=100, help="Max reviews per professor")
    parser.add_argument("--min-ratings", type=int, default=5, help="Require more than this many ratings")
    parser.add_argument(
        "--max-review-age-years",
        type=int,
        default=5,
        help="Require a review within this many years; only save reviews this recent",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max professors (for testing)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--no-resume", action="store_true", help="Start fresh, ignore checkpoint")
    args = parser.parse_args()

    scrape_school(
        school_id=args.school_id,
        university=args.university,
        review_count=args.review_count,
        min_ratings=args.min_ratings,
        max_review_age_years=args.max_review_age_years,
        limit=args.limit,
        delay=args.delay,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
