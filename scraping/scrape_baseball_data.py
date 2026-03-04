"""Program 1 (part A): scrape year links from Baseball Almanac.
This file collects year pages and saves raw + cleaned CSV files.
"""
import logging
import sys
import time
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR, SCRAPING_LOG_DIR
from scraping.common import build_driver, setup_logging

LOG_DIR = SCRAPING_LOG_DIR
RAW_OUTPUT = DATA_DIR / "years_raw.csv"
CLEAN_OUTPUT = DATA_DIR / "years_cleaned.csv"
URL = "https://www.baseball-almanac.com/yearmenu.shtml"

# Extract all year links like 1876, 1877, ... from the current page.
def extract_year_links(driver: webdriver.Chrome) -> list[dict]:
    links = driver.find_elements(By.TAG_NAME, "a")
    rows = []
    for link in links:
        text = (link.text or "").strip()
        href = link.get_attribute("href")
        if not text or not href:
            continue
        if text.isdigit() and len(text) == 4:
            rows.append(
                {
                    "year": int(text),
                    "url": href.strip(),
                }
            )
    return rows

# Try to move to the next page when pagination exists.
def try_go_to_next_page(driver: webdriver.Chrome) -> bool:
    next_candidates = driver.find_elements(
        By.XPATH,
        "//a[contains(translate(normalize-space(text()), 'NEXT', 'next'), 'next')]",
    )
    if not next_candidates:
        return False
    next_link = next_candidates[0]
    href = next_link.get_attribute("href")
    if not href:
        return False
    driver.get(href)
    time.sleep(1.5)
    return True

# Main scraping loop: open site, collect rows, and stop on repeated pages.
def scrape_year_links(start_url: str = URL, headless: bool = True, max_pages: int = 10) -> pd.DataFrame:
    driver = build_driver(headless=headless)
    all_rows: list[dict] = []
    try:
        driver.get(start_url)
        time.sleep(2)
        visited_urls = set()
        for page_number in range(1, max_pages + 1):
            current_url = driver.current_url
            if current_url in visited_urls:
                logging.warning("Detected repeated page URL, stopping pagination: %s", current_url)
                break

            visited_urls.add(current_url)
            page_rows = extract_year_links(driver)
            logging.info("Page %s: collected %s candidate rows", page_number, len(page_rows))
            all_rows.extend(page_rows)
            moved = try_go_to_next_page(driver)
            if not moved:
                break
    finally:
        driver.quit()
    return pd.DataFrame(all_rows)

# Basic cleaning: remove bad rows, remove duplicates, sort by year.
def clean_year_links(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year", "url"])

    cleaned = df.copy()
    cleaned["year"] = pd.to_numeric(cleaned["year"], errors="coerce").astype("Int64")
    cleaned["url"] = cleaned["url"].astype(str).str.strip()

    before_rows = len(cleaned)
    cleaned = cleaned.dropna(subset=["year", "url"])
    cleaned = cleaned[cleaned["year"].between(1800, 2100)]
    cleaned = cleaned[cleaned["url"] != ""]
    cleaned = cleaned.drop_duplicates(subset=["year", "url"]).sort_values("year")
    cleaned = cleaned.reset_index(drop=True)

    logging.info("Cleaning complete: %s -> %s rows", before_rows, len(cleaned))
    return cleaned

# Script entry point.
def main() -> None:
    setup_logging(LOG_DIR / "scrape_baseball_data.log")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("Starting scrape: %s", URL)
    raw_df = scrape_year_links(headless=True)
    raw_df.to_csv(RAW_OUTPUT, index=False)
    logging.info("Saved raw CSV: %s (%s rows)", RAW_OUTPUT, len(raw_df))

    cleaned_df = clean_year_links(raw_df)
    cleaned_df.to_csv(CLEAN_OUTPUT, index=False)
    logging.info("Saved cleaned CSV: %s (%s rows)", CLEAN_OUTPUT, len(cleaned_df))

    print(cleaned_df.head())

if __name__ == "__main__":
    main()