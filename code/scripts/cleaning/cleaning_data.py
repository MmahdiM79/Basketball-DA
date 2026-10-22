import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parents[2] / "DB" / "basketbal_da.db"


def clean_common(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace, turn empty strings into missing values, drop duplicate rows."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]):
            s = df[col].str.strip()
            df[col] = s.mask(s == "")
    return df.drop_duplicates()


def clean_players(df: pd.DataFrame) -> pd.DataFrame:
    df["birth_date"] = pd.to_datetime(df["birth_date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")
    df["height_cm"] = df["height_cm"].round(1)
    df["weight_kg"] = df["weight_kg"].round(1)
    return df


# Table-specific cleaners (tables not listed here only get the common cleaning)
SPECIFIC = {"Players": clean_players}


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
            conn,
        )["name"]

        for table in tables:
            raw = pd.read_sql(f'SELECT * FROM "{table}"', conn)
            df = clean_common(raw.copy())
            if table in SPECIFIC:
                df = SPECIFIC[table](df)

            out_path = HERE / f"{table.lower()}_clean.csv"
            df.to_csv(out_path, index=False, encoding="utf-8")
            print(f"{table}: {len(raw)} -> {len(df)} rows -> {out_path.name}")


if __name__ == "__main__":
    main()