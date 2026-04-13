"""Build a training feature matrix from DuckDB tables using `sql/features/*.sql` aggregates."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_SQL_DIR = _REPO_ROOT / "sql" / "features"
FEATURES_PATH = "data/features.parquet"


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


def _run_aggregations(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Run feature SQL and merge onto ``application_train`` (uncached)."""
    app = conn.execute("SELECT * FROM application_train").df()
    app = _normalize_sk_id_curr(app)

    bureau = load_feature_table(conn, "bureau_summary.sql")
    bureau_balance = load_feature_table(conn, "bureau_balance_summary.sql")
    previous_apps = load_feature_table(conn, "previous_applications.sql")
    installments = load_feature_table(conn, "installments_payments.sql")

    return (
        app.merge(bureau, on="SK_ID_CURR", how="left")
        .merge(bureau_balance, on="SK_ID_CURR", how="left")
        .merge(previous_apps, on="SK_ID_CURR", how="left")
        .merge(installments, on="SK_ID_CURR", how="left")
    )


def build_feature_matrix(
    conn: duckdb.DuckDBPyConnection, force_rebuild: bool = False
) -> pd.DataFrame:
    """Load or build the training feature matrix; cache at ``FEATURES_PATH`` under the repo root."""
    path = _REPO_ROOT / FEATURES_PATH
    if not force_rebuild and path.exists():
        return pd.read_parquet(path)

    df = _run_aggregations(conn)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_features_parquet(df, path)
    return df


def _write_features_parquet(df: pd.DataFrame, path: Path) -> None:
    """Persist features to Parquet via DuckDB (avoids pandas ``to_parquet`` / pyarrow hotfix edge cases)."""
    tmp = duckdb.connect()
    try:
        tmp.register("_feature_matrix", df)
        tmp.execute("COPY _feature_matrix TO ? (FORMAT PARQUET)", [str(path.resolve())])
    finally:
        tmp.close()
