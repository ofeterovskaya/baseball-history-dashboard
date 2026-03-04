import argparse
import sqlite3
import sys
from pathlib import Path
import pandas as pd

# Program 3: simple CLI query with JOIN between events and years.
# Make project root imports available when running this file directly.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DB_PATH

QUERY = """
SELECT
    e.year,
    e.event_text,
    e.source_url AS event_page_url,
    y.url AS year_page_url
FROM events e
LEFT JOIN (
    SELECT year, MIN(url) AS url
    FROM years
    GROUP BY year
) y ON y.year = e.year
WHERE (:year IS NULL OR e.year = :year)
    AND (:keyword IS NULL OR LOWER(e.event_text) LIKE LOWER(:keyword_like))
LIMIT :limit
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query baseball.db with SQL JOIN.")
    parser.add_argument("--year", type=int, default=None, help="Filter by year, example: --year 1998")
    parser.add_argument("--keyword", type=str, default=None, help="Filter event text, example: --keyword world")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to display")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}. Run database/import_to_sqlite.py first.")
        return

    with sqlite3.connect(DB_PATH) as connection:
        result = pd.read_sql_query(
            QUERY,
            connection,
            params={
                "year": args.year,
                "keyword": args.keyword,
                "keyword_like": f"%{args.keyword}%" if args.keyword else None,
                "limit": args.limit,
            },
        )

    if result.empty:
        print("No rows found for your filters.")
        return

    print(result.to_string(index=False, max_colwidth=80))

if __name__ == "__main__":
    main()
