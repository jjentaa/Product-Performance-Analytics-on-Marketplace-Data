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

tab_analytics, tab_model, tab_insight, tab_pipeline, tab_caveat = st.tabs(
    ["📈 Analytics (Q1–Q5)", "🤖 Model Insights (B1–B5)", "💡 Insights & Recommendations",
     "🔧 Pipeline", "⚠️ Data Limitations"]
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

# ═══════════════════════════════════════ TAB: INSIGHTS ════════════════════════════════════════
with tab_insight:
    st.markdown("### 💡 Insights & Business Recommendations")
    st.caption("Computed live from data under the current filter — change the sidebar filters and these numbers update.")

    seg2 = dl.get_reviewer_segment_stats(CATS, YRS, VER)
    bias2 = dl.get_price_missingness_bias(CATS, YRS, VER)
    imgs2 = dl.get_images_helpfulness(CATS, YRS, VER)

    def _seg_val(seg_name, col):
        row = seg2[seg2.reviewer_segment == seg_name]
        return row[col].iloc[0] if not row.empty else None

    oneoff_share = (seg2.loc[seg2.reviewer_segment == "One-off", "n_reviews"].sum() / seg2.n_reviews.sum()
                    if not seg2.empty and seg2.n_reviews.sum() > 0 else None)
    oneoff_pol = _seg_val("One-off", "polarized_share")
    power_pol = _seg_val("Power reviewer", "polarized_share")

    insights = []

    if oneoff_share is not None:
        insights.append((
            "1. Overall ratings are dominated by one-off reviewers",
            f"{oneoff_share:.0%} of reviews come from people who reviewed only once (one-off), and this "
            f"group gives extreme 1-or-5-star ratings {oneoff_pol:.0%} of the time, vs. {power_pol:.0%} "
            "for power reviewers"
            if power_pol is not None else "",
            "When reporting a product's average rating, always state the reviewer base, and use the "
            "one-off + not-verified group as a starting point for fake-review screening "
            "(see Model Insights tab, B5)",
        ))

    if not bias2.empty:
        unk = bias2.set_index("grp")
        if "Known price" in unk.index and "Unknown price" in unk.index:
            gap2 = unk.loc["Known price", "avg_rating"] - unk.loc["Unknown price", "avg_rating"]
            unk_pct = unk.loc["Unknown price", "pct"]
            insights.append((
                "2. Price is missing not-at-random (MNAR) — it biases price-based analysis",
                f"Price is unknown for {unk_pct:.0f}% of reviews, and products with a known price rate "
                f"{gap2:+.2f} stars higher on average than those without",
                "Any time price is analyzed (e.g. price_band vs rating), report what % of reviews were "
                "dropped, and never generalize the conclusion to all products.",
            ))

    if not imgs2.empty:
        piv = imgs2.pivot(index="category", columns="has_images", values="share_any_vote")
        if True in piv.columns and False in piv.columns:
            uplift = (piv[True] - piv[False]).mean()
            insights.append((
                "3. Reviews with photos are clearly trusted more",
                f"Share of reviews with ≥1 helpful vote is {uplift:+.1%} higher on average when a photo "
                "is attached, but photo reviews are only ~6% of all reviews",
                "Make it easier to attach photos in the UX (e.g. a more visible attach button), or "
                "incentivize photo reviews (coupons/points) to raise the share of high-quality reviews",
            ))

    b1i = dl.load_model_output("b1_regression_metrics.json")
    if b1i is not None:
        best = b1i.loc[b1i.MAE.idxmin()]
        baseline = b1i[b1i.model.str.contains("Baseline")].iloc[0]
        if best["model"] == baseline["model"]:
            insights.append((
                "4. Price/brand/category alone can't predict a new product's rating",
                "None of the regression models (Ridge, GradientBoosting) beat the baseline (predicting "
                "the category average) at all",
                "Don't use price/brand alone to screen new products before listing — invest in features "
                "from product description text, or wait for a real review count before evaluating",
            ))

    b5i_impact = dl.load_model_output("b5_impact_summary.csv")
    b5i_cand = dl.load_model_output("b5_anomaly_candidates.csv")
    if b5i_impact is not None and b5i_cand is not None:
        n_inflated2 = int((b5i_impact.delta < 0).sum())
        insights.append((
            "5. Some products may have their rating 'inflated' by suspicious reviews",
            f"Out of the 100 reviews the Anomaly Detection model flagged as most suspicious, {len(b5i_impact)} "
            f"products are affected, and {n_inflated2} of them would see their rating **drop** if the "
            "suspicious reviews were removed (meaning they were likely inflated)",
            "Send this product list to the Trust & Safety team for review first — results are only "
            "'suspicious', never penalize a user based on this score directly, a human must always review",
        ))

    b4i_words = dl.load_model_output("b4_topic_words.csv")
    b4i_cat = dl.load_model_output("b4_category_topic_share.csv")
    if b4i_words is not None and b4i_cat is not None and not b4i_cat.empty:
        num_cols = [c for c in b4i_cat.columns if c != "category"]
        top_topic_per_cat = b4i_cat.set_index("category")[num_cols].idxmax(axis=1)
        lines = []
        for cat, tid in top_topic_per_cat.items():
            words = b4i_words[(b4i_words.topic_id == int(tid)) & (b4i_words["rank"] <= 3)].word.tolist()
            lines.append(f"{cat} → {', '.join(words)}")
        insights.append((
            "6. Each category has a clearly distinct top complaint",
            " | ".join(lines),
            "Route each category's most common topic to the product/copywriting team that owns it, "
            "instead of applying a one-size-fits-all fix across the whole portfolio",
        ))

    insights.append((
        "7. Don't read the drop in 2022–2023 review volume as shrinking demand",
        "Review count fell from ~468K (2021) to ~58K (2023), which is a limitation of the source data "
        "collection (only through Sep 2023), not an actual drop in customer interest",
        "Report trends with average rating rather than review count from 2022 onward, and exclude "
        "incomplete years from volume-based comparison charts",
    ))

    for title, finding, rec in insights:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            if finding:
                st.write(finding)
            st.markdown(f"➡️ **Recommendation:** {rec}")

# ═══════════════════════════════════════ TAB: PIPELINE ═════════════════════════════════════════
with tab_pipeline:
    st.markdown("### 🔧 How the data gets here — ELT + ML pipeline")
    st.caption(
        "An overview of the pipeline behind this dashboard, from raw Amazon Reviews 2023 JSONL "
        "to the star schema and pre-trained models this page reads from."
    )

    st.markdown("#### 1. ELT pipeline (not ETL)")
    st.markdown(
        "Raw data is extracted and loaded first, then transformed **inside DuckDB with SQL** — "
        "instead of transforming in application code before loading. This keeps every "
        "transformation inspectable as plain SQL and lets DuckDB do the heavy lifting directly "
        "on Parquet files."
    )

    stage_cols = st.columns(5)
    stages = [
        ("1️⃣ Extract", "elt/extract.py", "Download raw review + metadata JSONL for the 3 categories from the Amazon Reviews 2023 source on Hugging Face."),
        ("2️⃣ Load", "elt/load.py", "Load raw JSONL into DuckDB as staging tables, no transformation yet."),
        ("3️⃣ Transform", "elt/sql/*.sql", "SQL builds staging → dimensions → facts, incl. a clean_text() macro that strips HTML/entities from review text, plus 10 automated quality checks."),
        ("4️⃣ Export", "elt/export.py", "Write the resulting star schema out to partitioned Parquet files."),
        ("5️⃣ Publish", "elt/publish.py", "Push the Parquet dataset to a public Hugging Face dataset repo, so the dashboard (and anyone else) can read it with zero setup."),
    ]
    for col, (name, path, desc) in zip(stage_cols, stages):
        with col:
            st.markdown(f"**{name}**")
            st.code(path, language=None)
            st.caption(desc)

    st.markdown(
        "Every stage stops the pipeline if a quality check fails (`elt/sql/40_quality_checks.sql`) "
        "— verified by deliberately feeding it bad data during testing and confirming the export "
        "step never runs."
    )

    st.divider()

    st.markdown("#### 2. Star schema (dataset #1)")
    svg_path = Path(__file__).resolve().parents[1] / "docs" / "star_schema.svg"
    col_schema, col_tables = st.columns([3, 2])
    with col_schema:
        if svg_path.exists():
            st.image(str(svg_path), width="stretch")
        else:
            st.info("star_schema.svg not found at docs/star_schema.svg")
    with col_tables:
        st.markdown(
            "- **fact_review** — 1 row per review (grain), ~3.66M rows\n"
            "- **review_text** — full review text, split out from the fact table\n"
            "- **dim_product** — product attributes, price band, brand\n"
            "- **dim_user** — reviewer segment (One-off / Regular / Power reviewer)\n"
            "- **dim_date** — calendar attributes for the review timestamp\n\n"
            "Engine: **DuckDB**, querying Parquet files directly — no database server needed."
        )

    st.divider()

    st.markdown("#### 3. ML pipeline (questions B1–B5)")
    st.markdown(
        "`preprocessing/` builds train/val/test splits (by review year) and features from "
        "dataset #2 (analytics-ready). `model/model.ipynb` trains all 5 models against those "
        "splits, evaluates each one against a baseline, and saves every model plus its output "
        "table to disk. **This dashboard only loads those saved files — it never retrains "
        "live**, which is why the Model Insights tab doesn't react to the year/verified filters."
    )
    model_rows = pd.DataFrame([
        {"Question": "B1", "Task": "Regression", "Model": "Ridge / GradientBoosting vs baseline", "Predicts": "Rating for products with a known price"},
        {"Question": "B2", "Task": "Classification", "Model": "TF-IDF + Logistic Regression", "Predicts": "Sentiment, to catch rating/text mismatches"},
        {"Question": "B3", "Task": "Clustering", "Model": "K-Means", "Predicts": "Performance-based product groups"},
        {"Question": "B4", "Task": "Topic Modeling", "Model": "LDA", "Predicts": "Complaint topics in negative reviews"},
        {"Question": "B5", "Task": "Anomaly Detection", "Model": "Isolation Forest + TF-IDF near-dup", "Predicts": "Reviews suspicious of being fake/paid"},
    ])
    st.dataframe(model_rows, hide_index=True, width="stretch")

    with st.expander("Artifacts loaded by this dashboard"):
        art_col1, art_col2 = st.columns(2)
        with art_col1:
            st.markdown("**Trained models** (`data/model_artifacts/`)")
            artifacts = dl.model_artifacts_available()
            if artifacts:
                for name in sorted(artifacts):
                    st.caption(f"✅ {name}.joblib")
            else:
                st.caption("None found yet — run `model/model.ipynb`")
        with art_col2:
            st.markdown("**Result tables** (`data/model_output/`)")
            for fname in sorted({
                "b1_regression_metrics.json", "b2_mismatch_reviews.csv", "b3_cluster_profile.csv",
                "b3_product_clusters.parquet", "b4_topic_words.csv", "b4_category_topic_share.csv",
                "b4_yearly_topic_share.csv", "b5_anomaly_candidates.csv", "b5_impact_summary.csv",
            }):
                exists = (dl.MODEL_OUTPUT_DIR / fname).exists()
                st.caption(f"{'✅' if exists else '❌'} {fname}")

    st.divider()

    st.markdown("#### 4. Tech stack")
    st.markdown(
        "`DuckDB` · `Parquet` · `pandas` / `pyarrow` · `scikit-learn` · `Hugging Face Hub` "
        "(dataset hosting) · `Streamlit` + `Plotly` (this dashboard)"
    )
    st.caption("Full details: `elt/` for the ELT pipeline source, `model/model.ipynb` for training code, `docs/business_questions.md` for every SQL query behind Q1–Q6.")

# ═══════════════════════════════════════ TAB: CAVEATS ══════════════════════════════════════════
with tab_caveat:
    st.markdown("### ⚠️ Data limitations to know before using this dashboard")
    st.markdown("""
- **No sales data** — review count is only a rough proxy for demand, don't read it as revenue or market share
- **Selection bias** — only people who chose to review are represented; very happy/unhappy customers tend
  to review more than neutral ones, so the average rating skews higher than true overall satisfaction
- **Price is missing on ~79% of reviews, not-at-random (MNAR)** — see the Analytics tab, Q3, for details
- **2022-onward review volume is incomplete** — the source dataset was only collected through Sep 2023
- **`dim_user` is computed from these 3 categories only**, not a user's full Amazon purchase history
- **B1 (regression)** only applies to products with a known price (~21% of reviews), which already rate above average
- **B2 has a distribution shift** — the share of negative reviews is naturally higher in test than in train
- **B4 (topic modeling)** — topic names come from automatically extracted top words; read real sample
  reviews before drawing conclusions
- **B5 (anomaly detection) gives "suspicious", not "confirmed fake"** — there's no verified label,
  never use it to penalize a user directly, use it for initial screening with a human review only
    """)
    st.caption(
        "Full details: `docs/business_questions.md` · "
        "`analytics/Answer_Analytic.ipynb` · `model/model.ipynb`"
    )
