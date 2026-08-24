"""ตัวสร้างกราฟ Plotly ทั้งหมดของ dashboard — แยกจาก app.py เพื่อให้อ่าน layout หลักง่ายขึ้น

หลักการเลือกชนิดกราฟ:
- แนวโน้มตามเวลา (ต่อเนื่อง)      -> line / dual-axis line+bar
- เทียบสัดส่วนระหว่างกลุ่ม (composition) -> 100% stacked bar
- จัดอันดับ (ranking)             -> horizontal bar เรียงค่า
- เทียบ 2 ตัวแปรต่อเนื่อง + กลุ่ม   -> scatter / bubble
- เทียบค่าระหว่าง 2-3 กลุ่มย่อย     -> grouped bar
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
        title=title,
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        template="plotly_white",
    )
    return fig


def yearly_trend(df: pd.DataFrame, incomplete_from_year: int = 2022) -> go.Figure:
    """[Time series] ปริมาณรีวิว + คะแนนเฉลี่ยรายปี — โซนแดงคือปีที่เก็บข้อมูลไม่ครบ"""
    fig = go.Figure()
    fig.add_bar(x=df.year, y=df.n_reviews, name="จำนวนรีวิว",
               marker_color="#B2BEC3", yaxis="y")
    fig.add_scatter(x=df.year, y=df.avg_rating, name="คะแนนเฉลี่ย", mode="lines+markers",
                    line=dict(color=POSITIVE_COLOR, width=3), yaxis="y2")
    if not df.empty and df.year.max() >= incomplete_from_year:
        fig.add_vrect(x0=incomplete_from_year - 0.5, x1=df.year.max() + 0.5,
                      fillcolor=INCOMPLETE_YEAR_COLOR, line_width=0,
                      annotation_text="ข้อมูลเก็บไม่ครบ", annotation_position="top left")
    fig.update_layout(
        yaxis=dict(title="จำนวนรีวิว"),
        yaxis2=dict(title="คะแนนเฉลี่ย", overlaying="y", side="right", range=[1, 5]),
        xaxis=dict(title="ปี", dtick=1),
    )
    return _base_layout(fig, "แนวโน้มปริมาณรีวิวและคะแนนเฉลี่ยรายปี")


def category_rating_distribution(df: pd.DataFrame) -> go.Figure:
    """[Comparison] สัดส่วนคะแนน 1-5 ดาว เทียบข้ามหมวด — 100% stacked bar"""
    pivot = df.pivot(index="category", columns="rating", values="n").fillna(0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0) * 100
    colors = {1: "#D63031", 2: "#E17055", 3: "#FDCB6E", 4: "#81C995", 5: "#00B894"}
    fig = go.Figure()
    for r in sorted(pivot.columns):
        fig.add_bar(y=pivot.index, x=pivot[r], name=f"{int(r)} ดาว",
                   orientation="h", marker_color=colors.get(r, NEUTRAL_COLOR))
    fig.update_layout(barmode="stack", xaxis_title="สัดส่วน (%)", yaxis_title="")
    return _base_layout(fig, "สัดส่วนคะแนนรีวิว เทียบข้ามหมวด (100% stacked)")


def top_brands(df: pd.DataFrame) -> go.Figure:
    """[Ranking] แบรนด์คะแนนดีที่สุด (เฉพาะที่มีรีวิวมากพอ) — horizontal bar"""
    d = df.sort_values("avg_rating")
    fig = px.bar(
        d, x="avg_rating", y="brand", color="category", orientation="h",
        color_discrete_map=CATEGORY_COLORS,
        hover_data={"n_reviews": ":,", "negative_share": ":.1%"},
        labels={"avg_rating": "คะแนนเฉลี่ย", "brand": ""},
    )
    fig.update_xaxes(range=[1, 5])
    return _base_layout(fig, "แบรนด์ที่คะแนนดีที่สุด (รีวิว ≥ 300)", height=440)


def price_band_rating(df: pd.DataFrame) -> go.Figure:
    """[Comparison] คะแนนเฉลี่ยตามช่วงราคา — bar chart (ลำดับ ordinal)"""
    order = ["Budget (<$10)", "Low ($10-25)", "Mid ($25-50)", "High ($50-100)", "Premium ($100+)"]
    d = df.set_index("price_band").reindex([o for o in order if o in df.price_band.values]).reset_index()
    fig = px.bar(d, x="price_band", y="avg_rating", text="n_reviews",
                color="avg_rating", color_continuous_scale="Teal",
                labels={"price_band": "", "avg_rating": "คะแนนเฉลี่ย"})
    fig.update_traces(texttemplate="%{text:,} รีวิว", textposition="outside")
    fig.update_yaxes(range=[0, 5.3])
    fig.update_layout(coloraxis_showscale=False)
    return _base_layout(fig, "คะแนนเฉลี่ยตามช่วงราคา (เฉพาะสินค้าที่รู้ราคา)")


def price_missingness_bias(df: pd.DataFrame) -> go.Figure:
    """[Comparison] คะแนนของกลุ่มที่รู้ราคา vs ไม่รู้ราคา — พิสูจน์ว่าราคาที่หายไม่สุ่ม"""
    fig = px.bar(df, x="grp", y="avg_rating", text="pct", color="grp",
                color_discrete_sequence=["#B2BEC3", "#0984E3"],
                labels={"grp": "", "avg_rating": "คะแนนเฉลี่ย"})
    fig.update_traces(texttemplate="%{text}%% ของรีวิว", textposition="outside")
    fig.update_yaxes(range=[0, 5.3])
    fig.update_layout(showlegend=False)
    return _base_layout(fig, "คะแนนเฉลี่ย: รู้ราคา vs ไม่รู้ราคา", height=340)


def reviewer_segment_comparison(df: pd.DataFrame) -> go.Figure:
    """[Comparison] คะแนนเฉลี่ย + ความแตกขั้ว ของแต่ละกลุ่มผู้รีวิว — grouped bar"""
    order = ["One-off", "Regular", "Power reviewer"]
    d = df.set_index("reviewer_segment").reindex([o for o in order if o in df.reviewer_segment.values]).reset_index()
    fig = go.Figure()
    fig.add_bar(x=d.reviewer_segment, y=d.avg_rating, name="คะแนนเฉลี่ย",
               marker_color="#0984E3", yaxis="y")
    fig.add_bar(x=d.reviewer_segment, y=d.polarized_share * 100, name="สัดส่วนให้ 1 หรือ 5 ดาว (%)",
               marker_color="#D63031", yaxis="y2")
    fig.update_layout(
        barmode="group",
        yaxis=dict(title="คะแนนเฉลี่ย", range=[0, 5.3]),
        yaxis2=dict(title="สัดส่วนแตกขั้ว (%)", overlaying="y", side="right", range=[0, 100]),
    )
    return _base_layout(fig, "One-off vs ขาประจำ: คะแนนและความแตกขั้ว")


def images_helpfulness(df: pd.DataFrame) -> go.Figure:
    """[Comparison] สัดส่วนรีวิวที่ได้โหวต 'มีประโยชน์' — มีรูป vs ไม่มีรูป"""
    d = df.copy()
    d["has_images"] = d.has_images.map({True: "มีรูป", False: "ไม่มีรูป"})
    fig = px.bar(d, x="category", y="share_any_vote", color="has_images", barmode="group",
                color_discrete_sequence=["#B2BEC3", "#00B894"],
                labels={"share_any_vote": "สัดส่วนที่ได้ ≥1 helpful vote", "category": ""})
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "รีวิวมีรูปได้โหวต 'มีประโยชน์' มากกว่าไหม")


def complaint_keywords(df: pd.DataFrame) -> go.Figure:
    """[Comparison] สัดส่วนคำบ่นที่พบในรีวิวเชิงลบ เทียบข้ามหมวด"""
    fig = px.bar(df, x="keyword_th", y="share", color="category", barmode="group",
                color_discrete_map=CATEGORY_COLORS,
                labels={"share": "สัดส่วนของรีวิวเชิงลบที่มีคำนี้", "keyword_th": ""})
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "คำบ่นที่พบในรีวิวเชิงลบ (1-2 ดาว) เทียบข้ามหมวด")


def timebomb_bar(df: pd.DataFrame) -> go.Figure:
    """[Ranking] สินค้ารีวิวเยอะแต่คะแนนต่ำ — ต้องแก้ก่อน"""
    d = df.head(12).copy()
    d["label"] = d.product_title.str.slice(0, 40) + "…"
    d = d.sort_values("n_reviews")
    fig = px.bar(d, x="n_reviews", y="label", orientation="h", color="avg_rating",
                color_continuous_scale="Reds_r", range_color=[1, 3],
                hover_data={"brand": True, "avg_rating": ":.2f"},
                labels={"n_reviews": "จำนวนรีวิว", "label": ""})
    return _base_layout(fig, "สินค้า 'ระเบิดเวลา' — รีวิวเยอะแต่คะแนนเฉลี่ย < 3", height=420)


def b1_model_comparison(df: pd.DataFrame) -> go.Figure:
    """[Comparison] MAE ของ Baseline vs Ridge vs GradientBoosting — ยิ่งต่ำยิ่งดี"""
    d = df.sort_values("MAE")
    colors = ["#00B894" if m == d.iloc[0]["model"] else "#B2BEC3" for m in d["model"]]
    fig = go.Figure(go.Bar(x=d.MAE, y=d.model, orientation="h", marker_color=colors,
                           text=d.MAE.round(4), textposition="outside"))
    fig.update_layout(xaxis_title="MAE (ยิ่งน้อยยิ่งดี)", yaxis_title="")
    return _base_layout(fig, "B1 — MAE ของแต่ละโมเดลเทียบ baseline", height=300)


def b2_f1_comparison(baseline_f1: float, model_f1: float) -> go.Figure:
    """[Comparison] macro-F1 baseline vs โมเดลจริง"""
    d = pd.DataFrame({"model": ["Baseline (ทาย positive เสมอ)", "TF-IDF + Logistic Regression"],
                      "macro_f1": [baseline_f1, model_f1]})
    fig = go.Figure(go.Bar(x=d.macro_f1, y=d.model, orientation="h",
                           marker_color=["#B2BEC3", "#0984E3"],
                           text=d.macro_f1.round(3), textposition="outside"))
    fig.update_layout(xaxis_title="macro-F1", yaxis_title="", xaxis_range=[0, 1])
    return _base_layout(fig, "B2 — macro-F1: โมเดลจริง vs baseline", height=260)


def b3_cluster_bubble(df: pd.DataFrame) -> go.Figure:
    """[Scatter/Bubble] โปรไฟล์แต่ละ cluster — ขนาดฟองคือจำนวนสินค้า"""
    fig = px.scatter(
        df, x="avg_rating", y="negative_share", size="n_products", color="cluster_name",
        hover_data={"rating_std": ":.2f", "polarized_share": ":.1%", "verified_share": ":.1%",
                   "n_products": ":,"},
        labels={"avg_rating": "คะแนนเฉลี่ยของสินค้าในกลุ่ม", "negative_share": "สัดส่วนรีวิวเชิงลบ"},
        size_max=60,
    )
    fig.update_yaxes(tickformat=".0%")
    return _base_layout(fig, "B3 — โปรไฟล์กลุ่มสินค้าที่ได้จาก Clustering", height=420)


def b3_cluster_size(df: pd.DataFrame) -> go.Figure:
    """[Composition] สัดส่วนจำนวนสินค้าต่อกลุ่ม"""
    fig = px.pie(df, names="cluster_name", values="n_products", hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textinfo="label+percent")
    return _base_layout(fig, "B3 — สัดส่วนจำนวนสินค้าต่อกลุ่ม", height=380)


def b4_topic_share_category(df: pd.DataFrame, topic_labels: dict) -> go.Figure:
    """[Composition] สัดส่วนหัวข้อการบ่น เทียบข้ามหมวด — stacked bar"""
    d = df.rename(columns=topic_labels)
    fig = go.Figure()
    for col in d.columns[1:]:
        fig.add_bar(y=d.category, x=d[col] * 100, name=col, orientation="h")
    fig.update_layout(barmode="stack", xaxis_title="สัดส่วนของรีวิวเชิงลบ (%)", yaxis_title="")
    return _base_layout(fig, "B4 — หัวข้อที่ถูกบ่นถึง เทียบข้ามหมวด", height=380)


def b4_topic_share_year(df: pd.DataFrame, topic_labels: dict) -> go.Figure:
    """[Time series] สัดส่วนหัวข้อการบ่นตามปี — ดูว่าหัวข้อไหนกำลังโตขึ้น"""
    d = df.rename(columns=topic_labels).sort_values("review_year")
    fig = go.Figure()
    for col in d.columns[1:]:
        fig.add_scatter(x=d.review_year, y=d[col] * 100, name=col, mode="lines+markers", stackgroup=None)
    fig.update_layout(xaxis_title="ปี", yaxis_title="สัดส่วนของรีวิวเชิงลบ (%)")
    return _base_layout(fig, "B4 — แนวโน้มหัวข้อการบ่นตามปี", height=380)


def b5_impact_bar(df: pd.DataFrame) -> go.Figure:
    """[Ranking] สินค้าที่คะแนนเปลี่ยนมากที่สุดถ้าตัดรีวิวต้องสงสัยออก"""
    d = df.reindex(df.delta.abs().sort_values(ascending=False).index).head(15)
    d = d.sort_values("delta")
    colors = [NEGATIVE_COLOR if v < 0 else POSITIVE_COLOR for v in d.delta]
    fig = go.Figure(go.Bar(x=d.delta, y=d.parent_asin, orientation="h", marker_color=colors,
                           text=d.delta.round(2), textposition="outside"))
    fig.update_layout(xaxis_title="คะแนนเปลี่ยนไป (excl. flagged − all)", yaxis_title="parent_asin")
    return _base_layout(fig, "B5 — ผลกระทบต่อคะแนนสินค้าถ้าตัดรีวิวต้องสงสัยออก", height=440)
