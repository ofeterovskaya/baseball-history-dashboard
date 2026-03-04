"""Program 2: import CSV files into SQLite.
This file creates baseball.db and imports each CSV file as a separate table.
"""
import logging
import re
import sqlite3
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR, DB_DIR, DB_PATH

# Configure simple console logging for import progress.
def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )

# Make safe SQL-friendly names for tables/columns.
def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "col"

# Use CSV file name as table name.
def table_name_from_file(csv_path: Path) -> str:
    return normalize_name(csv_path.stem)

# Rename duplicated/invalid columns to clean names.
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    used_names: set[str] = set()
    for col in df.columns:
        base_name = normalize_name(str(col))
        final_name = base_name
        suffix = 2
        while final_name in used_names:
            final_name = f"{base_name}_{suffix}"
            suffix += 1
        renamed[col] = final_name
        used_names.add(final_name)
    return df.rename(columns=renamed)

# Basic DataFrame cleanup before writing into SQLite.
def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = normalize_columns(df)
    for col in cleaned.columns:
        if cleaned[col].dtype == object:
            cleaned[col] = cleaned[col].astype(str).str.strip()
    for col in ["year", "event_rank", "source_element_index"]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    return cleaned

# Import one CSV file into one SQLite table.
def import_csv_to_table(connection: sqlite3.Connection, csv_path: Path) -> tuple[str, int]:
    table_name = table_name_from_file(csv_path)
    df = pd.read_csv(csv_path)
    if df.empty and len(df.columns) == 0:
        raise ValueError(f"CSV has no columns: {csv_path}")
    df = prepare_dataframe(df)
    df.to_sql(table_name, connection, if_exists="replace", index=False)
    logging.info("Imported %s -> table '%s' (%s rows)", csv_path.name, table_name, len(df))
    return table_name, len(df)

# Create indexes on common columns used in queries.
def create_helpful_indexes(connection: sqlite3.Connection, table_names: list[str]) -> None:
    cursor = connection.cursor()
    for table in table_names:
        columns = {
            row[1].lower()
            for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if "year" in columns:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_year ON {table}(year)")
        if "url" in columns:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_url ON {table}(url)")
        if "source_url" in columns:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_source_url ON {table}(source_url)")

    connection.commit()

# Import every CSV in data/ into database/baseball.db.
def import_all_csvs(data_dir: Path = DATA_DIR, db_path: Path = DB_PATH) -> None:
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    imported_tables: list[str] = []
    with sqlite3.connect(db_path) as connection:
        for csv_file in csv_files:
            table_name, _ = import_csv_to_table(connection, csv_file)
            imported_tables.append(table_name)

        create_helpful_indexes(connection, imported_tables)

        overview = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            connection,
        )
        logging.info("Database ready: %s", db_path)
        logging.info("Tables: %s", ", ".join(overview["name"].tolist()))

    # Script entry point.
def main() -> None:
    setup_logging()
    import_all_csvs()

if __name__ == "__main__":
    main()
