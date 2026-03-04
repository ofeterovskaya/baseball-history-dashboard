import logging
import os
import re
import sqlite3
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def resolve_path(env_name: str, default_path: Path) -> Path:
    raw_value = os.getenv(env_name)
    if not raw_value:
        raise RuntimeError(f"Missing required environment variable: {env_name}")
    candidate = Path(raw_value).expanduser()
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


DATA_DIR = resolve_path("DATA_DIR", BASE_DIR / "data")
DB_DIR = resolve_path("DB_DIR", BASE_DIR / "database")
DB_PATH = resolve_path("DB_PATH", DB_DIR / "baseball.db")

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )

def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "col"

def table_name_from_file(csv_path: Path) -> str:
    return normalize_name(csv_path.stem)

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

def infer_types(df: pd.DataFrame) -> pd.DataFrame:
    converted = df.copy()
    for col in converted.columns:
        series = converted[col]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        if series.dtype != object:
            continue
        stripped = series.astype(str).str.strip()
        stripped = stripped.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        numeric_candidate = pd.to_numeric(stripped, errors="coerce")
        numeric_ratio = numeric_candidate.notna().mean()
        if numeric_ratio >= 0.9 and numeric_candidate.notna().sum() > 0:
            converted[col] = numeric_candidate
            continue

        non_null_values = stripped.dropna().astype(str)
        looks_date_like = non_null_values.str.contains(
            r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
            case=False,
            regex=True,
        ).mean() >= 0.5 if not non_null_values.empty else False

        if looks_date_like:
            datetime_candidate = pd.to_datetime(stripped, errors="coerce")
            datetime_ratio = datetime_candidate.notna().mean()
            if datetime_ratio >= 0.9 and datetime_candidate.notna().sum() > 0:
                converted[col] = datetime_candidate.astype(str)
                continue
        converted[col] = stripped
    return converted

def import_csv_to_table(connection: sqlite3.Connection, csv_path: Path) -> tuple[str, int]:
    table_name = table_name_from_file(csv_path)
    df = pd.read_csv(csv_path)
    if df.empty and len(df.columns) == 0:
        raise ValueError(f"CSV has no columns: {csv_path}")
    df = normalize_columns(df)
    df = infer_types(df)
    df.to_sql(table_name, connection, if_exists="replace", index=False)
    logging.info("Imported %s -> table '%s' (%s rows)", csv_path.name, table_name, len(df))
    return table_name, len(df)

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

def main() -> None:
    setup_logging()
    import_all_csvs()

if __name__ == "__main__":
    main()
