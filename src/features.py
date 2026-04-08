"""Build a training feature matrix from DuckDB tables using `sql/features/*.sql` aggregates."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_SQL_DIR = _REPO_ROOT / "sql" / "features"


def _normalize_sk_id_curr(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the applicant id column is named ``SK_ID_CURR`` for consistent merges."""
    for col in list(df.columns):
        if str(col).upper() == "SK_ID_CURR":
            if col != "SK_ID_CURR":
                return df.rename(columns={col: "SK_ID_CURR"})
            break
    return df


def load_feature_table(conn: duckdb.DuckDBPyConnection, sql_file: str | Path) -> pd.DataFrame:
    """Run a feature SQL file and return a dataframe with ``SK_ID_CURR`` normalized."""
    path = Path(sql_file)
    if not path.is_absolute():
        path = FEATURE_SQL_DIR / path
    query = path.read_text()
    df = conn.execute(query).df()
    return _normalize_sk_id_curr(df)


def build_feature_matrix(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Left-join per-applicant feature aggregates onto ``application_train``."""
    app = conn.execute("SELECT * FROM application_train").df()
    app = _normalize_sk_id_curr(app)

    bureau = load_feature_table(conn, "bureau_summary.sql")
    bureau_balance = load_feature_table(conn, "bureau_balance_summary.sql")
    previous_apps = load_feature_table(conn, "previous_applications.sql")

    return (
        app.merge(bureau, on="SK_ID_CURR", how="left")
        .merge(bureau_balance, on="SK_ID_CURR", how="left")
        .merge(previous_apps, on="SK_ID_CURR", how="left")
    )
