import argparse
import logging
import re
import time
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

try:
    from scraping.common import BASE_DIR, build_driver, resolve_path, setup_logging
except ModuleNotFoundError:
    from common import BASE_DIR, build_driver, resolve_path, setup_logging


DATA_DIR = resolve_path("DATA_DIR", BASE_DIR / "data")
LOG_DIR = resolve_path("SCRAPING_LOG_DIR", BASE_DIR / "scraping" / "logs")
YEARS_CANDIDATES = [DATA_DIR / "years_cleaned.csv", DATA_DIR / "years.csv"]
RAW_OUTPUT = DATA_DIR / "events_raw.csv"
CLEAN_OUTPUT = DATA_DIR / "events.csv"
BAD_TEXT_PARTS = [
    "privacy policy",
    "terms of service",
    "all rights reserved",
    "copyright",
    "baseball almanac",
    "follow us",
    "click here",
    "advertis",
]

def get_years_input() -> Path:
    for candidate in YEARS_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Years source file not found. Run scraping/scrape_baseball_data.py first "
        "to create data/years.csv or data/years_cleaned.csv."
    )

def load_year_links(max_years: int | None = None) -> pd.DataFrame:
    years_path = get_years_input()
    df = pd.read_csv(years_path)
    if "year" not in df.columns or "url" not in df.columns:
        raise ValueError("Years CSV must contain 'year' and 'url' columns.")

    df = df[["year", "url"]].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["url"] = df["url"].astype(str).str.strip()
    df = df.dropna(subset=["year", "url"])
    df = df[df["url"] != ""]
    df["year"] = df["year"].astype(int)
    df = df.sort_values("year").drop_duplicates(subset=["year", "url"]).reset_index(drop=True)
    if max_years is not None and max_years > 0:
        df = df.head(max_years)
    return df

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def is_event_like_text(text: str) -> bool:
    text_lc = text.lower()
    if len(text) < 25 or len(text) > 400:
        return False
    if any(part in text_lc for part in BAD_TEXT_PARTS):
        return False
    if text_lc in {"home", "menu", "next", "previous"}:
        return False
    has_digit = any(ch.isdigit() for ch in text)
    has_action_word = any(
        word in text_lc
        for word in [
            "won",
            "hit",
            "game",
            "world series",
            "league",
            "record",
            "home run",
            "pitch",
            "season",
        ]
    )
    return has_digit or has_action_word

def extract_events_on_page(driver: webdriver.Chrome, year: int, source_url: str, max_events_per_year: int = 80) -> list[dict]:
    candidates = driver.find_elements(By.CSS_SELECTOR, "li, p")
    rows: list[dict] = []
    seen_texts: set[str] = set()
    for idx, element in enumerate(candidates, start=1):
        raw_text = element.text or ""
        text = normalize_text(raw_text)
        if not text or not is_event_like_text(text):
            continue
        key = text.lower()
        if key in seen_texts:
            continue
        seen_texts.add(key)
        rows.append(
            {
                "year": year,
                "event_rank": len(rows) + 1,
                "event_text": text,
                "source_url": source_url,
                "source_element_index": idx,
            }
        )
        if len(rows) >= max_events_per_year:
            break
    return rows

def scrape_events(year_links: pd.DataFrame, headless: bool = True, pause_seconds: float = 1.2) -> pd.DataFrame:
    driver = build_driver(headless=headless)
    all_rows: list[dict] = []
    try:
        for position, row in year_links.iterrows():
            year = int(row["year"])
            url = str(row["url"])
            logging.info("[%s/%s] Scraping events for year %s", position + 1, len(year_links), year)
            driver.get(url)
            time.sleep(pause_seconds)
            year_rows = extract_events_on_page(driver, year=year, source_url=url)
            logging.info("Year %s: extracted %s event candidates", year, len(year_rows))
            all_rows.extend(year_rows)
    finally:
        driver.quit()
    return pd.DataFrame(all_rows)

def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year", "event_rank", "event_text", "source_url", "source_element_index"])

    cleaned = df.copy()
    cleaned["year"] = pd.to_numeric(cleaned["year"], errors="coerce").astype("Int64")
    cleaned["event_rank"] = pd.to_numeric(cleaned["event_rank"], errors="coerce").astype("Int64")
    cleaned["source_element_index"] = pd.to_numeric(cleaned["source_element_index"], errors="coerce").astype("Int64")
    cleaned["event_text"] = cleaned["event_text"].astype(str).apply(normalize_text)
    cleaned["source_url"] = cleaned["source_url"].astype(str).str.strip()
    before_rows = len(cleaned)
    cleaned = cleaned.dropna(subset=["year", "event_text", "source_url"])
    cleaned = cleaned[cleaned["event_text"] != ""]
    cleaned = cleaned.drop_duplicates(subset=["year", "event_text"])
    cleaned = cleaned.sort_values(["year", "event_rank", "source_element_index"], na_position="last")
    cleaned = cleaned.reset_index(drop=True)
    logging.info("Events cleaning complete: %s -> %s rows", before_rows, len(cleaned))
    return cleaned

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape yearly baseball events from Baseball Almanac.")
    parser.add_argument("--max-years", type=int, default=None, help="Limit years to scrape for quick testing.")
    parser.add_argument("--show-browser", action="store_true", help="Run browser in non-headless mode.")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    setup_logging(LOG_DIR / "scrape_year_events.log")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    year_links = load_year_links(max_years=args.max_years)
    logging.info("Loaded %s year links", len(year_links))
    raw_df = scrape_events(year_links, headless=not args.show_browser)
    raw_df.to_csv(RAW_OUTPUT, index=False)
    logging.info("Saved raw events CSV: %s (%s rows)", RAW_OUTPUT, len(raw_df))
    cleaned_df = clean_events(raw_df)
    cleaned_df.to_csv(CLEAN_OUTPUT, index=False)
    logging.info("Saved cleaned events CSV: %s (%s rows)", CLEAN_OUTPUT, len(cleaned_df))

    print(cleaned_df.head())

if __name__ == "__main__":
    main()
