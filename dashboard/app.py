"""Interactive Dashboard — Amazon Reviews 2023: Beauty & Personal Care

Run with:
    streamlit run dashboard/app.py

Data sources:
- Analytics tab (Q1-Q5): live queries via DuckDB on **dataset #1 (star schema produced
  by the ELT pipeline)** — answered purely with counts/averages, no model needed
- Model Insights tab (B1-B5): loads results from models that were **trained and saved
  ahead of time** under data/model_output/ (tables) and data/model_artifacts/
  (.joblib models) from model/model.ipynb — the dashboard never retrains live
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import charts
import data_loader as dl

st.set_page_config(page_title="Amazon Beauty Reviews — Dashboard", page_icon="📊", layout="wide")

# ─────────────────────────────────────────── Header ───────────────────────────────────────────
st.title("📊 Product Performance Dashboard")
st.caption(
    "Amazon Reviews 2023 · Beauty & Personal Care categories (All_Beauty, Amazon_Fashion, "
    "Health_and_Personal_Care) · data from dataset #1 (through the ELT pipeline) + "
    "pre-trained models (B1–B5)"
)

# ─────────────────────────────────────────── Sidebar: Filters ───────────────────────────────────
bounds = dl.get_filter_bounds()

st.sidebar.header("🔎 Filter")
sel_categories = st.sidebar.multiselect(
    "Category", options=bounds["categories"], default=bounds["categories"],
)
sel_year_range = st.sidebar.slider(
    "Review year range", min_value=bounds["year_min"], max_value=bounds["year_max"],
    value=(bounds["year_min"], bounds["year_max"]),
)
sel_verified_only = st.sidebar.checkbox("Verified purchases only", value=False)

if sel_year_range[1] >= 2022:
    st.sidebar.warning(
        "⚠️ Data from 2022 onward is incomplete (the source dataset was collected through "
        "Sep 2023) — don't read a drop in review volume as shrinking demand, look at the "
        "average rating instead"
    )

if not sel_categories:
    st.warning("Select at least 1 category in the sidebar to see data")
    st.stop()

CATS = tuple(sorted(sel_categories))
YRS = tuple(sel_year_range)
VER = bool(sel_verified_only)

with st.sidebar.expander("🧠 Models used in the Model Insights tab"):
    artifacts = dl.model_artifacts_available()
    if artifacts:
        for name in sorted(artifacts):
            st.caption(f"✅ {name}.joblib")
    else:
        st.caption("No model files found yet — run `model/model.ipynb` first")

# ─────────────────────────────────────────── KPI Row ────────────────────────────────────────────
kpi = dl.get_kpis(CATS, YRS, VER)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Reviews", f"{kpi['n_reviews']:,.0f}")
k2.metric("Avg Rating", f"{kpi['avg_rating']:.2f} ⭐")
k3.metric("Negative Share", f"{kpi['negative_share']:.1%}")
k4.metric("Verified Share", f"{kpi['verified_share']:.1%}")

st.divider()

tab_analytics, tab_model = st.tabs(
    ["📈 Analytics (Q1–Q5)", "🤖 Model Insights (B1–B5)"]
)

# ═══════════════════════════════════════ TAB: ANALYTICS ═══════════════════════════════════════
with tab_analytics:
    st.markdown(
        "Answered purely with counts/averages on **dataset #1 (star schema)** — no model "
        "needed. Every chart is a live query against the filters in the sidebar."
    )

    st.subheader("Trend over time — how has review volume and satisfaction moved year by year?")
    trend = dl.get_yearly_trend(CATS, YRS, VER)
    st.plotly_chart(charts.yearly_trend(trend), width="stretch")

    st.subheader("Q1 — Do one-off reviewers rate differently from regulars?")
    st.caption(
        "Almost everyone is a one-off reviewer. If this group rates more extremely, the "
        "overall rating is being dominated by love-it-or-hate-it opinions."
    )
    seg = dl.get_reviewer_segment_stats(CATS, YRS, VER)
    st.plotly_chart(charts.reviewer_segment_comparison(seg), width="stretch")

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.subheader("Q2 — Which products are 'time bombs'? (lots of reviews, low rating)")
        st.caption("A problem hitting many people matters more than a low-rated product only a few people bought.")
        timebomb = dl.get_timebomb_products(CATS, YRS, VER)
        if timebomb.empty:
            st.info("No products meet this criteria within the current filter")
        else:
            st.plotly_chart(charts.timebomb_bar(timebomb), width="stretch")
    with col_b:
        st.subheader("Q6 — Which brands are strongest?")
        st.caption("A benchmark for comparing our brands against competitors")
        brands = dl.get_top_brands(CATS, YRS, VER)
        if brands.empty:
            st.info("No brand has ≥ 300 reviews within the current filter")
        else:
            st.plotly_chart(charts.top_brands(brands), width="stretch")

    st.subheader("Q3 — Price is missing on ~79% of reviews — how much does that bias the analysis?")
    bias = dl.get_price_missingness_bias(CATS, YRS, VER)
    price = dl.get_price_band_rating(CATS, YRS, VER)
    if not bias.empty:
        unknown_pct = bias.loc[bias.grp == "Unknown price", "pct"]
        gap = (bias.set_index("grp").avg_rating.get("Known price", 0)
              - bias.set_index("grp").avg_rating.get("Unknown price", 0))
        st.warning(
            f"⚠️ Price is unknown for **{unknown_pct.iloc[0] if len(unknown_pct) else 0:.0f}%** of reviews, "
            f"and the known-price group rates **{gap:+.2f} stars** higher than the unknown-price group "
            "→ dropping 'Unknown' rows skews the analysis positive, it's not just a smaller sample."
        )
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.price_missingness_bias(bias), width="stretch")
    with col_d:
        if not price.empty:
            st.plotly_chart(charts.price_band_rating(price), width="stretch")
        else:
            st.info("No products with a known price within the current filter")

    st.subheader("Q4 — Are reviews with photos actually more helpful? Worth promoting?")
    st.caption("Reviews with photos are rare (~6%) — if they demonstrably help buyers decide, it's worth improving the UX to make attaching photos easier.")
    imgs = dl.get_images_helpfulness(CATS, YRS, VER)
    st.plotly_chart(charts.images_helpfulness(imgs), width="stretch")

    st.subheader("Q5 — What do customers complain about in negative reviews? (keyword version)")
    st.caption(
        "Counted with SQL `LIKE` — fast and easy to explain, but has no context understanding "
        "(e.g. \"great quality\" still matches the word quality). Compare against the topic "
        "modeling version (B4) in the Model Insights tab."
    )
    kw = dl.get_complaint_keyword_share(CATS, YRS, VER)
    if kw.empty:
        st.info("No negative reviews within the current filter")
    else:
        st.plotly_chart(charts.complaint_keywords(kw), width="stretch")

# ═══════════════════════════════════════ TAB: MODEL INSIGHTS ══════════════════════════════════
with tab_model:
    st.markdown(
        "Results from models that were **trained and saved ahead of time** in `model/model.ipynb` "
        "(models live under `data/model_artifacts/*.joblib`, result tables under `data/model_output/`). "
        "This tab does not retrain live — charts don't change with the year/verified filters in the "
        "sidebar (except for the category filter, in places that join back to live data)."
    )

    # ── B1: Regression ─────────────────────────────────────────────────────────────────────
    st.subheader("B1 — What rating will a new product get? (Regression)")
    st.caption("A new product has no reviews yet, so `GROUP BY` averages don't work — it has to learn from existing products.")
    b1 = dl.load_model_output("b1_regression_metrics.json")
    if b1 is None:
        st.info("No B1 results yet — run `model/model.ipynb` first")
    else:
        best_row = b1.loc[b1.MAE.idxmin()]
        baseline_row = b1[b1.model.str.contains("Baseline")].iloc[0]
        colb1, colb2 = st.columns([2, 3])
        with colb1:
            if best_row["model"] == baseline_row["model"]:
                st.error(
                    "**No model beats the baseline** on this real data — price, brand, and category "
                    "don't explain product ratings at all. Reporting this honestly; further work should "
                    "add features from product description text, not more model tuning."
                )
            else:
                gain = baseline_row.MAE - best_row.MAE
                st.success(f"Best model **{best_row['model']}** beats baseline by {gain:.4f} stars")
            st.dataframe(b1.style.format({"MAE": "{:.4f}", "RMSE": "{:.4f}", "R2": "{:.4f}"}),
                        hide_index=True, width="stretch")
        with colb2:
            st.plotly_chart(charts.b1_model_comparison(b1), width="stretch")

    st.divider()

    # ── B2: Classification ─────────────────────────────────────────────────────────────────
    st.subheader("B2 — Does the review text match the star rating given? (Classification)")
    st.caption(
        "The real value isn't the F1 score — it's finding reviews where the **rating doesn't match "
        "the text** (mis-clicked stars, sarcasm, rating for a free gift instead), which distorts a "
        "product's score."
    )
    b2_meta = dl.load_b2_metadata()
    b2_mismatch = dl.load_model_output("b2_mismatch_reviews.csv")
    if b2_meta is None:
        st.info("No B2 results yet — run `model/model.ipynb` first")
    else:
        colb3, colb4 = st.columns([2, 3])
        with colb3:
            st.metric("macro-F1 (trained model)", f"{b2_meta['macro_f1_test']:.3f}",
                      delta=f"{b2_meta['macro_f1_test'] - b2_meta['baseline_macro_f1']:+.3f} vs baseline")
            n_mismatch = 0 if b2_mismatch is None else len(b2_mismatch)
            st.metric("Rating/text mismatches (test set)", f"{n_mismatch:,}")
        with colb4:
            st.plotly_chart(
                charts.b2_f1_comparison(b2_meta["baseline_macro_f1"], b2_meta["macro_f1_test"]),
                width="stretch",
            )
        if b2_mismatch is not None and not b2_mismatch.empty:
            with st.expander(f"See example mismatched reviews ({len(b2_mismatch)} rows)"):
                st.dataframe(
                    b2_mismatch[["category", "rating", "mismatch_type", "p_negative", "p_positive", "text_full"]],
                    hide_index=True, width="stretch",
                )

    st.divider()

    # ── B3: Clustering ──────────────────────────────────────────────────────────────────────
    st.subheader("B3 — How many performance-based groups do products fall into? (Clustering)")
    st.caption("The number of groups isn't known in advance — let K-Means discover the structure from the data instead of hand-writing rules.")
    b3_profile = dl.load_model_output("b3_cluster_profile.csv")
    if b3_profile is None:
        st.info("No B3 results yet — run `model/model.ipynb` first")
    else:
        colb5, colb6 = st.columns([3, 2])
        with colb5:
            st.plotly_chart(charts.b3_cluster_bubble(b3_profile), width="stretch")
        with colb6:
            st.plotly_chart(charts.b3_cluster_size(b3_profile), width="stretch")

        sel_cluster = st.selectbox("🔍 Pick a cluster to see real sample products", b3_profile.cluster_name.tolist())
        sample = dl.get_products_in_cluster(sel_cluster, CATS)
        if sample.empty:
            st.caption("No sample products in this cluster for the selected categories")
        else:
            st.dataframe(sample, hide_index=True, width="stretch")

    st.divider()

    # ── B4: Topic modeling ──────────────────────────────────────────────────────────────────
    st.subheader("B4 — What are customers complaining about? (Topic Modeling)")
    st.caption("Knowing a 1-2 star review means 'unhappy' doesn't say *what about* — with hundreds of thousands of reviews, reading them by hand isn't feasible.")
    topic_words = dl.load_model_output("b4_topic_words.csv")
    cat_share = dl.load_model_output("b4_category_topic_share.csv")
    year_share = dl.load_model_output("b4_yearly_topic_share.csv")
    if topic_words is None or cat_share is None:
        st.info("No B4 results yet — run `model/model.ipynb` first")
    else:
        top3 = (topic_words[topic_words["rank"] <= 3]
               .groupby("topic_id")["word"].apply(lambda s: ", ".join(s)))
        topic_labels = {str(tid): f"T{tid}: {words}" for tid, words in top3.items()}

        colb7, colb8 = st.columns(2)
        with colb7:
            st.plotly_chart(charts.b4_topic_share_category(cat_share, topic_labels),
                            width="stretch")
        with colb8:
            if year_share is not None:
                st.plotly_chart(charts.b4_topic_share_year(year_share, topic_labels),
                                width="stretch")

        with st.expander("Top words per topic (top 8)"):
            top8 = (topic_words[topic_words["rank"] <= 8]
                   .groupby("topic_id")["word"].apply(lambda s: ", ".join(s)).reset_index())
            top8.columns = ["Topic", "Top words"]
            top8["Topic"] = top8["Topic"].map(lambda t: topic_labels.get(str(t), f"T{t}"))
            st.dataframe(top8, hide_index=True, width="stretch")

    st.divider()

    # ── B5: Anomaly detection ───────────────────────────────────────────────────────────────
    st.subheader("B5 — Which reviews look like they might be fake/paid? (Anomaly Detection)")
    st.caption(
        "There's no ground-truth label for which reviews are actually fake — results are "
        "**'suspicious', not 'confirmed fake'**. Use this for initial screening only, with a "
        "human always reviewing before acting on it."
    )
    b5_candidates = dl.load_model_output("b5_anomaly_candidates.csv")
    b5_impact = dl.load_model_output("b5_impact_summary.csv")
    if b5_candidates is None or b5_impact is None:
        st.info("No B5 results yet — run `model/model.ipynb` first")
    else:
        n_flagged = len(b5_candidates)
        n_products = len(b5_impact)
        n_inflated = int((b5_impact.delta < 0).sum())
        n_deflated = int((b5_impact.delta > 0).sum())
        avg_abs = b5_impact.delta.abs().mean()

        colb9, colb10, colb11, colb12 = st.columns(4)
        colb9.metric("Reviews flagged", f"{n_flagged:,}")
        colb10.metric("Products affected", f"{n_products:,}")
        colb11.metric("Ratings likely 'inflated'", f"{n_inflated} products")
        colb12.metric("Avg impact on rating", f"±{avg_abs:.3f} stars")

        st.plotly_chart(charts.b5_impact_bar(b5_impact), width="stretch")

        with st.expander("Most suspicious reviews — try tagging them yourself (not saved, just a demo of the human-review step)"):
            show_cols = ["review_id", "category", "rating", "anomaly_score", "verified_purchase",
                        "reviewer_segment", "near_dup_similarity", "text_full", "is_fake_manual_label"]
            edited = st.data_editor(
                b5_candidates[show_cols].head(30),
                hide_index=True, width="stretch",
                disabled=[c for c in show_cols if c != "is_fake_manual_label"],
                column_config={
                    "is_fake_manual_label": st.column_config.SelectboxColumn(
                        "Human review result", options=["", "fake", "genuine", "not sure"]
                    )
                },
            )
