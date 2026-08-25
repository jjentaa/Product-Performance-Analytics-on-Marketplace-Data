"""All Plotly chart builders for the dashboard — kept separate from app.py so the main layout stays readable.

Chart-type picking rules:
- Trend over time (continuous)        -> line / dual-axis line+bar
- Composition across groups           -> 100% stacked bar
- Ranking                             -> horizontal bar, sorted by value
- Two continuous variables + group    -> scatter / bubble
- Comparing 2-3 subgroups             -> grouped bar
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CATEGORY_COLORS = {
    "All_Beauty": "#6C5CE7",
    "Amazon_Fashion": "#00B894",
    "Health_and_Personal_Care": "#0984E3",
}
NEGATIVE_COLOR = "#D63031"
POSITIVE_COLOR = "#00B894"
NEUTRAL_COLOR = "#636E72"
INCOMPLETE_YEAR_COLOR = "rgba(214, 48, 49, 0.10)"


def _base_layout(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        height=height,
        margin=dict(l=10, r=10, t=48, b=70),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0),
        template="plotly_white",
    )
    return fig


def yearly_trend(df: pd.DataFrame, incomplete_from_year: int = 2022) -> go.Figure:
    """[Time series] Review volume + average rating per year — red zone marks incomplete years"""
    fig = go.Figure()
    fig.add_bar(x=df.year, y=df.n_reviews, name="Review count",
               marker_color="#B2BEC3", yaxis="y")
    fig.add_scatter(x=df.year, y=df.avg_rating, name="Avg rating", mode="lines+markers",
                    line=dict(color=POSITIVE_COLOR, width=3), yaxis="y2")
    if not df.empty and df.year.max() >= incomplete_from_year:
        fig.add_vrect(x0=incomplete_from_year - 0.5, x1=df.year.max() + 0.5,
                      fillcolor=INCOMPLETE_YEAR_COLOR, line_width=0,
                      annotation_text="Incomplete data", annotation_position="top left")
    fig.update_layout(
        yaxis=dict(title="Review count"),
        yaxis2=dict(title="Avg rating", overlaying="y", side="right", range=[1, 5]),
        xaxis=dict(title="Year", dtick=1),
    )
    return _base_layout(fig, "Yearly trend — review volume and average rating")


def category_rating_distribution(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Share of 1-5 star ratings across categories — 100% stacked bar"""
    pivot = df.pivot(index="category", columns="rating", values="n").fillna(0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100
    colors = {1: "#D63031", 2: "#E17055", 3: "#FDCB6E", 4: "#81C995", 5: "#00B894"}
    fig = go.Figure()
    for r in sorted(pivot.columns):
        fig.add_bar(y=pivot.index, x=pivot[r], name=f"{int(r)} star",
                   orientation="h", marker_color=colors.get(r, NEUTRAL_COLOR))
    fig.update_layout(barmode="stack", xaxis_title="Share (%)", yaxis_title="")
    return _base_layout(fig, "Rating distribution across categories (100% stacked)")


def top_brands(df: pd.DataFrame) -> go.Figure:
    """[Ranking] Best-rated brands (with enough reviews) — horizontal bar"""
    d = df.sort_values("avg_rating")
    fig = px.bar(
        d, x="avg_rating", y="brand", color="category", orientation="h",
        color_discrete_map=CATEGORY_COLORS,
        hover_data={"n_reviews": ":,", "negative_share": ":.1%"},
        labels={"avg_rating": "Avg rating", "brand": ""},
    )
    fig.update_xaxes(range=[1, 5])
    return _base_layout(fig, "Best-rated brands (≥ 300 reviews)", height=440)


def price_band_rating(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Average rating by price band — bar chart (ordinal ordering)"""
    order = ["Budget (<$10)", "Low ($10-25)", "Mid ($25-50)", "High ($50-100)", "Premium ($100+)"]
    d = df.set_index("price_band").reindex([o for o in order if o in df.price_band.values]).reset_index()
    fig = px.bar(d, x="price_band", y="avg_rating", text="n_reviews",
                color="avg_rating", color_continuous_scale="Teal",
                labels={"price_band": "", "avg_rating": "Avg rating"})
    fig.update_traces(texttemplate="%{text:,} reviews", textposition="outside")
    fig.update_yaxes(range=[0, 5.3])
    fig.update_layout(coloraxis_showscale=False)
    return _base_layout(fig, "Average rating by price band (products with known price only)")


def price_missingness_bias(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Rating of known-price vs unknown-price groups — shows the missingness isn't random"""
    fig = px.bar(df, x="grp", y="avg_rating", text="pct", color="grp",
                color_discrete_sequence=["#B2BEC3", "#0984E3"],
                labels={"grp": "", "avg_rating": "Avg rating"})
    fig.update_traces(texttemplate="%{text}%% of reviews", textposition="outside")
    fig.update_yaxes(range=[0, 5.3])
    fig.update_layout(showlegend=False)
    return _base_layout(fig, "Avg rating: known price vs unknown price", height=340)


def reviewer_segment_comparison(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Avg rating + polarization of each reviewer segment — grouped bar"""
    order = ["One-off", "Regular", "Power reviewer"]
    d = df.set_index("reviewer_segment").reindex([o for o in order if o in df.reviewer_segment.values]).reset_index()
    fig = go.Figure()
    fig.add_bar(x=d.reviewer_segment, y=d.avg_rating, name="Avg rating",
               marker_color="#0984E3", yaxis="y")
    fig.add_bar(x=d.reviewer_segment, y=d.polarized_share * 100, name="Share giving 1 or 5 stars (%)",
               marker_color="#D63031", yaxis="y2")
    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Avg rating", range=[0, 5.3]),
        yaxis2=dict(title="Polarized share (%)", overlaying="y", side="right", range=[0, 100]),
    )
    return _base_layout(fig, "One-off vs regulars: rating and polarization")


def images_helpfulness(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Share of reviews voted 'helpful' — with images vs without"""
    d = df.copy()
    d["has_images"] = d.has_images.map({True: "With images", False: "No images"})
    fig = px.bar(d, x="category", y="share_any_vote", color="has_images", barmode="group",
                color_discrete_sequence=["#B2BEC3", "#00B894"],
                labels={"share_any_vote": "Share with ≥1 helpful vote", "category": ""})
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "Do reviews with images get voted 'helpful' more often?")


def complaint_keywords(df: pd.DataFrame) -> go.Figure:
    """[Comparison] Share of complaint keywords found in negative reviews, across categories"""
    fig = px.bar(df, x="keyword_label", y="share", color="category", barmode="group",
                color_discrete_map=CATEGORY_COLORS,
                labels={"share": "Share of negative reviews containing this keyword", "keyword_label": ""})
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "Complaint keywords found in negative reviews (1-2 star), by category")


def timebomb_bar(df: pd.DataFrame) -> go.Figure:
    """[Ranking] Products with lots of reviews but a low rating — need fixing first"""
    d = df.head(12).copy()
    d["label"] = d.product_title.str.slice(0, 40) + "…"
    d = d.sort_values("n_reviews")
    fig = px.bar(d, x="n_reviews", y="label", orientation="h", color="avg_rating",
                color_continuous_scale="Reds_r", range_color=[1, 3],
                hover_data={"brand": True, "avg_rating": ":.2f"},
                labels={"n_reviews": "Review count", "label": ""})
    return _base_layout(fig, "'Time bomb' products — many reviews but avg rating < 3", height=420)


def b1_model_comparison(df: pd.DataFrame) -> go.Figure:
    """[Comparison] MAE of Baseline vs Ridge vs GradientBoosting — lower is better"""
    d = df.sort_values("MAE")
    colors = ["#00B894" if m == d.iloc[0]["model"] else "#B2BEC3" for m in d["model"]]
    fig = go.Figure(go.Bar(x=d.MAE, y=d.model, orientation="h", marker_color=colors,
                           text=d.MAE.round(4), textposition="outside"))
    fig.update_layout(xaxis_title="MAE (lower is better)", yaxis_title="")
    return _base_layout(fig, "B1 — MAE of each model vs baseline", height=300)


def b2_f1_comparison(baseline_f1: float, model_f1: float) -> go.Figure:
    """[Comparison] macro-F1 baseline vs the trained model"""
    d = pd.DataFrame({"model": ["Baseline (always predicts positive)", "TF-IDF + Logistic Regression"],
                      "macro_f1": [baseline_f1, model_f1]})
    fig = go.Figure(go.Bar(x=d.macro_f1, y=d.model, orientation="h",
                           marker_color=["#B2BEC3", "#0984E3"],
                           text=d.macro_f1.round(3), textposition="outside"))
    fig.update_layout(xaxis_title="macro-F1", yaxis_title="", xaxis_range=[0, 1])
    return _base_layout(fig, "B2 — macro-F1: trained model vs baseline", height=260)


def b3_cluster_bubble(df: pd.DataFrame) -> go.Figure:
    """[Scatter/Bubble] Profile of each cluster — bubble size is product count"""
    fig = px.scatter(
        df, x="avg_rating", y="negative_share", size="n_products", color="cluster_name",
        hover_data={"rating_std": ":.2f", "polarized_share": ":.1%", "verified_share": ":.1%",
                   "n_products": ":,"},
        labels={"avg_rating": "Avg rating of products in cluster", "negative_share": "Negative review share"},
        size_max=60,
    )
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "B3 — Product cluster profiles from Clustering", height=420)


def b3_cluster_size(df: pd.DataFrame) -> go.Figure:
    """[Composition] Share of products per cluster"""
    fig = px.pie(df, names="cluster_name", values="n_products", hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textinfo="label+percent")
    return _base_layout(fig, "B3 — Share of products per cluster", height=380)


def b4_topic_share_category(df: pd.DataFrame, topic_labels: dict) -> go.Figure:
    """[Composition] Share of complaint topics across categories — stacked bar"""
    d = df.rename(columns=topic_labels)
    fig = go.Figure()
    for col in d.columns[1:]:
        fig.add_bar(y=d.category, x=d[col] * 100, name=col, orientation="h")
    fig.update_layout(barmode="stack", xaxis_title="Share of negative reviews (%)", yaxis_title="")
    return _base_layout(fig, "B4 — Complaint topics by category", height=380)


def b4_topic_share_year(df: pd.DataFrame, topic_labels: dict) -> go.Figure:
    """[Time series] Share of complaint topics over time — see which topics are trending up"""
    d = df.rename(columns=topic_labels).sort_values("review_year")
    fig = go.Figure()
    for col in d.columns[1:]:
        fig.add_scatter(x=d.review_year, y=d[col] * 100, name=col, mode="lines+markers", stackgroup=None)
    fig.update_layout(xaxis_title="Year", yaxis_title="Share of negative reviews (%)")
    return _base_layout(fig, "B4 — Complaint topic trend over time", height=380)


def b5_impact_bar(df: pd.DataFrame) -> go.Figure:
    """[Ranking] Products whose rating changes the most if flagged reviews are removed"""
    d = df.reindex(df.delta.abs().sort_values(ascending=False).index).head(15)
    d = d.sort_values("delta")
    colors = [NEGATIVE_COLOR if v < 0 else POSITIVE_COLOR for v in d.delta]
    fig = go.Figure(go.Bar(x=d.delta, y=d.parent_asin, orientation="h", marker_color=colors,
                           text=d.delta.round(2), textposition="outside"))
    fig.update_layout(xaxis_title="Rating change (excl. flagged − all)", yaxis_title="parent_asin")
    return _base_layout(fig, "B5 — Rating impact if suspicious reviews are removed", height=440)
