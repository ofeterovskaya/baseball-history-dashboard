# Baseball History Dashboard

This project scrapes historical baseball data from the Baseball Almanac website, stores it in a SQLite database, and presents insights through an interactive Streamlit dashboard.

## Project Components

1. Web Scraping Program – Uses Selenium to collect baseball history data.
2. Database Import Program – Imports scraped CSV data into a SQLite database.
3. Database Query Program – Allows command-line queries using SQL joins.
4. Dashboard – Interactive Streamlit dashboard for exploring the data.

## Data Source

https://www.baseball-almanac.com/yearmenu.shtml

## Project Structure

- `scraping/scrape_baseball_data.py` — Program 1A: scrape year links and save years CSV files.
- `scraping/scrape_year_events.py` — Program 1B: scrape event text for each year and save events CSV files.
- `database/import_to_sqlite.py` — Program 2: import all CSV files into SQLite tables.
- `queries/query_database.py` — Program 3: run CLI SQL JOIN queries with filters.
- `dashboard/app.py` — Program 4: Streamlit dashboard with interactive charts and keyword exploration.

## Setup

1. Create and activate virtual environment:
	- `python -m venv .venv`
	- `source .venv/Scripts/activate`
2. Install dependencies:
	- `pip install -r requirements.txt`
3. Create `.env` from `.env.example` and keep default paths (or customize if needed).

## Run Programs (Lesson Workflow)

### Program 1 — Web Scraping

1) Scrape years:
- `python scraping/scrape_baseball_data.py`

2) Scrape events by year:
- Full run: `python scraping/scrape_year_events.py`
- Quick test: `python scraping/scrape_year_events.py --max-years 5`

Outputs:
- `data/years_raw.csv`
- `data/years_cleaned.csv`
- `data/events_raw.csv`
- `data/events.csv`

### Program 2 — Database Import

- `python database/import_to_sqlite.py`

Output:
- `database/baseball.db`

### Program 3 — Database Query (CLI)

Examples:
- `python queries/query_database.py --year 1998 --limit 10`
- `python queries/query_database.py --keyword world --limit 10`
- `python queries/query_database.py --year 1927 --limit 10`

### Program 4 — Dashboard (Streamlit)

- `streamlit run dashboard/app.py`

## Dashboard Features

The dashboard includes:

1. **Evolution of Baseball Through Time** (line chart)
	- Year vs number of events.
2. **Most Dramatic Years in Baseball History** (Top 10 bar chart)
	- Years with the highest event volume.
3. **Top Keywords in Event Text** (bar chart)
	- Most frequent terms in selected data.
4. **Keyword Explorer**
	- Search event text by keyword (e.g., `home run`, `world series`, `strike`, `expansion`).
5. **Firsts in Baseball**
	- Quick filter for events containing `first`.
6. **Records and Milestones**
	- Filter for `record`, `milestone`, and `career`.

## Cleaning and Transformation Notes

- Raw and cleaned datasets are saved separately (before/after stage).
- Cleaning includes null handling, text normalization, duplicate removal, and sorting.
- Example from recent run:
  - Events raw: `4293` rows
  - Events cleaned: `2766` rows

## SQL and Join Validation

- Core query joins `events` and `years` on `year`.
- A grouped subquery (`MIN(url)`) is used to avoid duplicate join rows for the same year.

## Deployment

Available at your primary URL 
https://baseball-history-dashboard-k63p.onrender.com

## Screenshot
<img width="1865" height="835" alt="1" src="https://github.com/user-attachments/assets/15b0062c-4abf-4297-82eb-8d5addc2d6bf" />

<img width="1607" height="773" alt="2" src="https://github.com/user-attachments/assets/69eb5626-f796-4be4-9d92-e3bc65345b7e" />

<img width="1852" height="812" alt="3" src="https://github.com/user-attachments/assets/1d5ac494-6d40-4e2d-a284-ab526fef7220" />



