"""Dashboard data loaders — all cached so filtering stays responsive.

Primary data source: dataset #1 (star schema produced by the ELT pipeline) — every
live query that depends on a filter (category / year range / verified) runs through
DuckDB directly on this dataset's Parquet files.

Model results (B1-B5) come from models that were **trained and saved ahead of time**
under data/model_output/ (result tables) and data/model_artifacts/ (.joblib models) —
the dashboard only loads and displays them, it never retrains live.
"""

import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from elt.common import load_config, resolve_dataset  # noqa: E402

MODEL_OUTPUT_DIR = ROOT / "data" / "model_output"
MODEL_ARTIFACT_DIR = ROOT / "data" / "model_artifacts"

# If deployed on Streamlit Cloud with a secret named HF_TOKEN configured, bridge it
# into a normal HF_TOKEN env var — huggingface_hub picks it up automatically. This is
# a safe no-op if the secret isn't set, or when running locally with a .env already
# in place. Having a token raises Hugging Face's rate limit substantially, which
# matters a lot on cloud platforms where the outbound IP is often shared across apps.
if "HF_TOKEN" not in os.environ:
    try:
        if "HF_TOKEN" in st.secrets:
            os.environ["HF_TOKEN"] = st.secrets["HF_TOKEN"]
    except Exception:
        pass  # No secrets.toml at all (e.g. running locally) — not a problem


@st.cache_resource(show_spinner="Connecting to dataset (star schema from the ELT pipeline)...")
def get_connection() -> duckdb.DuckDBPyConnection:
    """Open DuckDB and create views over dataset #1 (already through the ELT pipeline)"""
    config = load_config()
    src = resolve_dataset("elt", config)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW fact_review AS SELECT * FROM '{src}/fact_review/**/*.parquet'")
    con.execute(f"CREATE VIEW review_text AS SELECT * FROM '{src}/review_text/**/*.parquet'")
    con.execute(f"CREATE VIEW dim_product AS SELECT * FROM '{src}/dim_product.parquet'")
    con.execute(f"CREATE VIEW dim_user   AS SELECT * FROM '{src}/dim_user.parquet'")
    con.execute(f"CREATE VIEW dim_date   AS SELECT * FROM '{src}/dim_date.parquet'")
    return con


@st.cache_data(show_spinner=False)
def get_filter_bounds() -> dict:
    """Bounds used to set up the sidebar widgets (category, year)"""
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    cats = con.execute(
        "SELECT DISTINCT category FROM fact_review ORDER BY 1"
    ).df()["category"].tolist()
    y0, y1 = con.execute(
        "SELECT min(year(review_ts)), max(year(review_ts)) FROM fact_review"
    ).fetchone()
    return {"categories": cats, "year_min": int(y0), "year_max": int(y1)}


def _where_clause(categories: list[str], year_range: tuple[int, int], verified_only: bool) -> str:
    cats = ", ".join(f"'{c}'" for c in categories)
    conds = [
        f"f.category IN ({cats})",
        f"year(f.review_ts) BETWEEN {year_range[0]} AND {year_range[1]}",
    ]
    if verified_only:
        conds.append("f.verified_purchase = TRUE")
    return " AND ".join(conds)


@st.cache_data(show_spinner=False)
def get_kpis(categories: tuple, year_range: tuple, verified_only: bool) -> dict:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    row = con.execute(f"""
        SELECT
            count(*)                                AS n_reviews,
            round(avg(f.rating), 3)                  AS avg_rating,
            round(avg(f.is_negative::INT), 4)         AS negative_share,
            round(avg(f.verified_purchase::INT), 4)   AS verified_share,
            count(DISTINCT f.product_key)             AS n_products,
            round(avg(f.has_images::INT), 4)          AS with_images_share
        FROM fact_review f WHERE {where}
    """).df().iloc[0].to_dict()
    return row


@st.cache_data(show_spinner=False)
def get_yearly_trend(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT year(f.review_ts) AS year, count(*) AS n_reviews,
               round(avg(f.rating), 3) AS avg_rating,
               round(avg(f.is_negative::INT), 4) AS negative_share
        FROM fact_review f WHERE {where}
        GROUP BY 1 ORDER BY 1
    """).df()


@st.cache_data(show_spinner=False)
def get_category_rating_distribution(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT f.category, f.rating, count(*) AS n
        FROM fact_review f WHERE {where}
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()


@st.cache_data(show_spinner=False)
def get_top_brands(categories: tuple, year_range: tuple, verified_only: bool, min_reviews: int = 300) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT p.store AS brand, p.category, count(*) AS n_reviews,
               round(avg(f.rating), 3) AS avg_rating,
               round(avg(f.is_negative::INT), 4) AS negative_share
        FROM fact_review f JOIN dim_product p USING (product_key)
        WHERE {where} AND p.store IS NOT NULL
        GROUP BY 1, 2 HAVING count(*) >= {min_reviews}
        ORDER BY avg_rating DESC LIMIT 15
    """).df()


@st.cache_data(show_spinner=False)
def get_price_band_rating(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT p.price_band, count(*) AS n_reviews,
               round(avg(f.rating), 3) AS avg_rating
        FROM fact_review f JOIN dim_product p USING (product_key)
        WHERE {where} AND p.price_band <> 'Unknown'
        GROUP BY 1
    """).df()


@st.cache_data(show_spinner=False)
def get_price_missingness_bias(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT CASE WHEN p.price IS NULL THEN 'Unknown price' ELSE 'Known price' END AS grp,
               count(*) AS n_reviews,
               round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct,
               round(avg(f.rating), 3) AS avg_rating
        FROM fact_review f JOIN dim_product p USING (product_key)
        WHERE {where}
        GROUP BY 1
    """).df()


@st.cache_data(show_spinner=False)
def get_reviewer_segment_stats(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT u.reviewer_segment, count(*) AS n_reviews,
               round(avg(f.rating), 3) AS avg_rating,
               round(avg((f.rating IN (1,5))::INT), 4) AS polarized_share,
               round(avg(f.verified_purchase::INT), 4) AS verified_share
        FROM fact_review f JOIN dim_user u USING (user_key)
        WHERE {where}
        GROUP BY 1
    """).df()


@st.cache_data(show_spinner=False)
def get_images_helpfulness(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        SELECT f.category, f.has_images,
               count(*) AS n_reviews,
               round(avg(f.helpful_vote), 3) AS avg_helpful,
               median(f.helpful_vote) AS median_helpful,
               round(avg((f.helpful_vote > 0)::INT), 4) AS share_any_vote
        FROM fact_review f WHERE {where}
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()


COMPLAINT_KEYWORDS = {
    "size_fit": "Size / fit",
    "quality": "Quality",
    "fake": "Counterfeit",
    "smell": "Smell",
    "refund_return": "Refund / return",
    "shipping": "Shipping",
}
_KEYWORD_PATTERNS = {
    "size_fit": ["size", "too small", "too big", "too large", "fit", "tight", "loose"],
    "quality": ["quality", "cheaply made", "cheap material", "flimsy", "poor quality"],
    "fake": ["fake", "counterfeit", "not authentic", "knock off", "knockoff"],
    "smell": ["smell", "odor", "scent", "stink"],
    "refund_return": ["refund", "return", "money back", "sent it back"],
    "shipping": ["shipping", "delivery", "arrived late", "package", "damaged in transit"],
}


@st.cache_data(show_spinner="Counting complaint keywords in negative reviews...")
def get_complaint_keyword_share(categories: tuple, year_range: tuple, verified_only: bool) -> pd.DataFrame:
    """Q5 (pure-analytics version) — share of complaint keywords found in negative reviews via LIKE

    This only counts *keyword presence*, with no context understanding (a rough picture).
    For a more accurate topic breakdown, see the B4 result (LDA topic modeling) in the
    Model Insights tab.
    """
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    rows = []
    for topic, patterns in _KEYWORD_PATTERNS.items():
        like_conds = " OR ".join(f"lower(t.review_text) LIKE '%{p}%'" for p in patterns)
        df = con.execute(f"""
            SELECT f.category,
                   round(avg(({like_conds})::INT), 4) AS share
            FROM fact_review f JOIN review_text t USING (review_id)
            WHERE {where} AND f.is_negative = TRUE
            GROUP BY 1
        """).df()
        df["keyword"] = topic
        df["keyword_label"] = COMPLAINT_KEYWORDS[topic]
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


@st.cache_data(show_spinner=False)
def get_timebomb_products(categories: tuple, year_range: tuple, verified_only: bool,
                          min_reviews: int = 100, max_rating: float = 3.0) -> pd.DataFrame:
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    where = _where_clause(list(categories), year_range, verified_only)
    return con.execute(f"""
        WITH per_product AS (
            SELECT f.product_key, count(*) AS n_reviews,
                   round(avg(f.rating), 2) AS avg_rating,
                   round(avg(f.is_negative::INT), 3) AS negative_share
            FROM fact_review f WHERE {where}
            GROUP BY 1 HAVING count(*) >= {min_reviews}
        )
        SELECT p.category, p.store AS brand, p.product_title, pp.n_reviews,
               pp.avg_rating, pp.negative_share
        FROM per_product pp JOIN dim_product p USING (product_key)
        WHERE pp.avg_rating < {max_rating}
        ORDER BY pp.n_reviews DESC LIMIT 20
    """).df()


# ────────────────────────── Pre-trained model results (B1-B5) ──────────────────────────

@st.cache_data(show_spinner=False)
def load_model_output(filename: str) -> pd.DataFrame | None:
    """Load a result table saved ahead of time by model/model.ipynb; None if not present yet"""
    path = MODEL_OUTPUT_DIR / filename
    if not path.exists():
        return None
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix == ".json":
        return pd.read_json(path)
    raise ValueError(f"Unknown file extension: {path}")


def model_artifacts_available() -> dict:
    """Check which models have been trained + saved already — used to decide which tab content to show"""
    if not MODEL_ARTIFACT_DIR.exists():
        return {}
    return {p.stem: p for p in MODEL_ARTIFACT_DIR.glob("*.joblib")}


@st.cache_resource(show_spinner=False)
def load_b2_metadata() -> dict | None:
    """Load just the metadata (macro-F1) from the pre-trained B2 model, without loading the predict pipeline"""
    import joblib
    path = MODEL_ARTIFACT_DIR / "b2_sentiment_classifier.joblib"
    if not path.exists():
        return None
    obj = joblib.load(path)
    return {"macro_f1_test": obj["macro_f1_test"], "baseline_macro_f1": obj["baseline_macro_f1"]}


@st.cache_data(show_spinner=False)
def get_products_in_cluster(cluster_name: str, categories: tuple, limit: int = 10) -> pd.DataFrame:
    """Sample real products from each cluster (B3) — joins the model output with live dim_product"""
    clusters = load_model_output("b3_product_clusters.parquet")
    if clusters is None:
        return pd.DataFrame()
    con = get_connection().cursor()  # per-call cursor avoids race conditions across overlapping reruns
    con.register("_clusters", clusters)
    cats = ", ".join(f"'{c}'" for c in categories) or "''"
    return con.execute(f"""
        SELECT p.product_title, p.store, p.listed_avg_rating, p.listed_rating_count, c.category
        FROM _clusters c
        JOIN dim_product p USING (product_key)
        WHERE c.cluster_name = ? AND c.category IN ({cats})
        ORDER BY p.listed_rating_count DESC NULLS LAST
        LIMIT {limit}
    """, [cluster_name]).df()
