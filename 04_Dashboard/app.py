"""Interactive Dashboard — Amazon Reviews 2023: Beauty & Personal Care

รันด้วย:
    streamlit run dashboard/app.py

แหล่งข้อมูล:
- แท็บ Analytics (Q1-Q5): query สดผ่าน DuckDB บน **dataset #1 (star schema ที่ผ่าน
  ELT pipeline แล้ว)** — ตอบได้ด้วยการนับ/ค่าเฉลี่ย ไม่ต้องใช้โมเดล
- แท็บ Model Insights (B1-B5): โหลดผลลัพธ์จากโมเดลที่ **เทรนและบันทึกไว้ล่วงหน้าแล้ว**
  ที่ data/model_output/ (ตาราง) และ data/model_artifacts/ (ตัวโมเดล .joblib)
  จาก model/model.ipynb — dashboard ไม่ retrain สดในแอป
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
    "Amazon Reviews 2023 · หมวด Beauty & Personal Care (All_Beauty, Amazon_Fashion, "
    "Health_and_Personal_Care) · ข้อมูลจาก dataset #1 (ผ่าน ELT pipeline) + "
    "โมเดลที่เทรนไว้ล่วงหน้า (B1–B5)"
)

# ─────────────────────────────────────────── Sidebar: Filters ───────────────────────────────────
bounds = dl.get_filter_bounds()

st.sidebar.header("🔎 Filter")
sel_categories = st.sidebar.multiselect(
    "หมวดสินค้า", options=bounds["categories"], default=bounds["categories"],
)
sel_year_range = st.sidebar.slider(
    "ช่วงปีของรีวิว", min_value=bounds["year_min"], max_value=bounds["year_max"],
    value=(bounds["year_min"], bounds["year_max"]),
)
sel_verified_only = st.sidebar.checkbox("เฉพาะรีวิวที่ซื้อจริง (verified purchase)", value=False)

if sel_year_range[1] >= 2022:
    st.sidebar.warning(
        "⚠️ ข้อมูลปี 2022 เป็นต้นไปเก็บไม่ครบ (ชุดข้อมูลต้นทางเก็บถึง ก.ย. 2023) "
        "อย่าตีความปริมาณรีวิวที่ลดลงว่าดีมานด์หด — ดูคะแนนเฉลี่ยแทน"
    )

if not sel_categories:
    st.warning("เลือกอย่างน้อย 1 หมวดสินค้าที่แถบด้านซ้ายเพื่อดูข้อมูล")
    st.stop()

CATS = tuple(sorted(sel_categories))
YRS = tuple(sel_year_range)
VER = bool(sel_verified_only)

with st.sidebar.expander("🧠 โมเดลที่ใช้ในแท็บ Model Insights"):
    artifacts = dl.model_artifacts_available()
    if artifacts:
        for name in sorted(artifacts):
            st.caption(f"✅ {name}.joblib")
    else:
        st.caption("ยังไม่พบไฟล์โมเดล — รัน `model/model.ipynb` ก่อน")

# ─────────────────────────────────────────── KPI Row ────────────────────────────────────────────
kpi = dl.get_kpis(CATS, YRS, VER)

k1, k2, k3, k4 = st.columns(4)
k1.metric("จำนวนรีวิว (Total Reviews)", f"{kpi['n_reviews']:,.0f}")
k2.metric("คะแนนเฉลี่ย (Avg Rating)", f"{kpi['avg_rating']:.2f} ⭐")
k3.metric("สัดส่วนรีวิวเชิงลบ (Negative Share)", f"{kpi['negative_share']:.1%}")
k4.metric("สัดส่วนซื้อจริง (Verified Share)", f"{kpi['verified_share']:.1%}")

st.divider()

tab_analytics, tab_model, tab_insight, tab_caveat = st.tabs(
    ["📈 Analytics (Q1–Q5)", "🤖 Model Insights (B1–B5)", "💡 Insights & ข้อเสนอแนะ", "⚠️ ข้อจำกัดของข้อมูล"]
)

# ═══════════════════════════════════════ TAB: ANALYTICS ═══════════════════════════════════════
with tab_analytics:
    st.markdown(
        "ตอบด้วยการนับ/ค่าเฉลี่ยล้วน ๆ บน **dataset #1 (star schema)** — ไม่ต้องสร้างโมเดล "
        "ทุกกราฟ query สดตาม filter ด้านซ้าย"
    )

    st.subheader("แนวโน้มตามเวลา — ปริมาณรีวิวและความพึงพอใจเป็นอย่างไรในแต่ละปี?")
    trend = dl.get_yearly_trend(CATS, YRS, VER)
    st.plotly_chart(charts.yearly_trend(trend), width="stretch")

    st.subheader("Q1 — คนรีวิวครั้งเดียว vs ขาประจำ ให้คะแนนต่างกันไหม?")
    st.caption(
        "คนเกือบทั้งหมดเป็น One-off ถ้ากลุ่มนี้ให้คะแนนสุดขั้วกว่า แปลว่าคะแนนรวมถูกครอบงำ"
        "ด้วยความเห็นแบบรัก-หรือ-เกลียด"
    )
    seg = dl.get_reviewer_segment_stats(CATS, YRS, VER)
    st.plotly_chart(charts.reviewer_segment_comparison(seg), width="stretch")

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.subheader("Q2 — สินค้าไหน \"ระเบิดเวลา\"? (รีวิวเยอะ แต่คะแนนต่ำ)")
        st.caption("ปัญหาที่กระทบคนจำนวนมากสำคัญกว่าสินค้าคะแนนต่ำที่มีคนซื้อไม่กี่คน")
        timebomb = dl.get_timebomb_products(CATS, YRS, VER)
        if timebomb.empty:
            st.info("ไม่พบสินค้าที่เข้าเกณฑ์ในช่วง filter นี้")
        else:
            st.plotly_chart(charts.timebomb_bar(timebomb), width="stretch")
    with col_b:
        st.subheader("Q6 — แบรนด์ไหนแข็งแกร่งที่สุด?")
        st.caption("Benchmark สำหรับเทียบผลงานของแบรนด์เรากับคู่แข่ง")
        brands = dl.get_top_brands(CATS, YRS, VER)
        if brands.empty:
            st.info("ไม่มีแบรนด์ที่มีรีวิว ≥ 300 ในช่วง filter นี้")
        else:
            st.plotly_chart(charts.top_brands(brands), width="stretch")

    st.subheader("Q3 — ราคาหาย ~79% บิดผลการวิเคราะห์แค่ไหน?")
    bias = dl.get_price_missingness_bias(CATS, YRS, VER)
    price = dl.get_price_band_rating(CATS, YRS, VER)
    if not bias.empty:
        unknown_pct = bias.loc[bias.grp == "ไม่รู้ราคา", "pct"]
        gap = (bias.set_index("grp").avg_rating.get("รู้ราคา", 0)
              - bias.set_index("grp").avg_rating.get("ไม่รู้ราคา", 0))
        st.warning(
            f"⚠️ ราคาไม่ทราบใน **{unknown_pct.iloc[0] if len(unknown_pct) else 0:.0f}%** ของรีวิว "
            f"และคะแนนของกลุ่มที่รู้ราคาสูงกว่ากลุ่มที่ไม่รู้ราคาอยู่ **{gap:+.2f} ดาว** "
            "→ การกรอง 'Unknown' ทิ้งทำให้ผลเอนไปทางบวก ไม่ใช่แค่ตัวอย่างเล็กลง"
        )
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.price_missingness_bias(bias), width="stretch")
    with col_d:
        if not price.empty:
            st.plotly_chart(charts.price_band_rating(price), width="stretch")
        else:
            st.info("ไม่มีสินค้าที่รู้ราคาในช่วง filter นี้")

    st.subheader("Q4 — รีวิวมีรูปมีประโยชน์กว่าจริงไหม คุ้มที่จะดันไหม?")
    st.caption("รีวิวมีรูปมีน้อยมาก (~6%) — ถ้าพิสูจน์ว่าช่วยคนอื่นตัดสินใจจริง ก็คุ้มออกแบบ UX ให้แนบรูปง่ายขึ้น")
    imgs = dl.get_images_helpfulness(CATS, YRS, VER)
    st.plotly_chart(charts.images_helpfulness(imgs), width="stretch")

    st.subheader("Q5 — ลูกค้าบ่นเรื่องอะไรในรีวิวเชิงลบ? (เวอร์ชัน keyword)")
    st.caption(
        "นับด้วย SQL `LIKE` — เร็วและอธิบายง่าย แต่ไม่เข้าใจบริบท (เช่น \"great quality\" ก็ติดคำว่า quality) "
        "เทียบผลกับเวอร์ชัน topic modeling (B4) ได้ที่แท็บ Model Insights"
    )
    kw = dl.get_complaint_keyword_share(CATS, YRS, VER)
    if kw.empty:
        st.info("ไม่มีรีวิวเชิงลบในช่วง filter นี้")
    else:
        st.plotly_chart(charts.complaint_keywords(kw), width="stretch")

# ═══════════════════════════════════════ TAB: MODEL INSIGHTS ══════════════════════════════════
with tab_model:
    st.markdown(
        "ผลลัพธ์จากโมเดลที่ **เทรนและบันทึกไว้ล่วงหน้าแล้ว** ใน `model/model.ipynb` "
        "(ตัวโมเดลอยู่ที่ `data/model_artifacts/*.joblib`, ตารางผลลัพธ์อยู่ที่ `data/model_output/`) "
        "แท็บนี้ไม่ retrain สด — กราฟจึงไม่เปลี่ยนตาม filter ปี/verified ด้านซ้าย "
        "(ยกเว้นตัวกรองหมวดในบางส่วนที่ join กับข้อมูลสดได้)"
    )

    # ── B1: Regression ─────────────────────────────────────────────────────────────────────
    st.subheader("B1 — สินค้าใหม่จะได้คะแนนเท่าไหร่? (Regression)")
    st.caption("สินค้าใหม่ยังไม่มีรีวิวเลย จะ `GROUP BY` หาค่าเฉลี่ยไม่ได้ ต้องเรียนรู้จากสินค้าที่มีอยู่แล้ว")
    b1 = dl.load_model_output("b1_regression_metrics.json")
    if b1 is None:
        st.info("ยังไม่มีผลลัพธ์ B1 — รัน `model/model.ipynb` ก่อน")
    else:
        best_row = b1.loc[b1.MAE.idxmin()]
        baseline_row = b1[b1.model.str.contains("Baseline")].iloc[0]
        colb1, colb2 = st.columns([2, 3])
        with colb1:
            if best_row["model"] == baseline_row["model"]:
                st.error(
                    "**ไม่มีโมเดลไหนชนะ baseline** ในข้อมูลจริงชุดนี้ — ราคา, แบรนด์, หมวด "
                    "อธิบายคะแนนสินค้าไม่ได้เลย ต้องรายงานตามตรง ถ้าจะทำต่อควรเพิ่ม feature "
                    "จากข้อความรายละเอียดสินค้า ไม่ใช่ปรับจูนโมเดลต่อ"
                )
            else:
                gain = baseline_row.MAE - best_row.MAE
                st.success(f"โมเดลดีที่สุด **{best_row['model']}** ดีกว่า baseline {gain:.4f} ดาว")
            st.dataframe(b1.style.format({"MAE": "{:.4f}", "RMSE": "{:.4f}", "R2": "{:.4f}"}),
                        hide_index=True, width="stretch")
        with colb2:
            st.plotly_chart(charts.b1_model_comparison(b1), width="stretch")

    st.divider()

    # ── B2: Classification ─────────────────────────────────────────────────────────────────
    st.subheader("B2 — ข้อความในรีวิวตรงกับดาวที่ให้ไหม? (Classification)")
    st.caption(
        "ประโยชน์จริงไม่ใช่ค่า F1 แต่คือการหารีวิวที่ **ดาวไม่ตรงข้อความ** "
        "(กดดาวผิด/ประชด/ให้ดาวตามของแถม) ซึ่งทำให้คะแนนสินค้าเพี้ยน"
    )
    b2_meta = dl.load_b2_metadata()
    b2_mismatch = dl.load_model_output("b2_mismatch_reviews.csv")
    if b2_meta is None:
        st.info("ยังไม่มีผลลัพธ์ B2 — รัน `model/model.ipynb` ก่อน")
    else:
        colb3, colb4 = st.columns([2, 3])
        with colb3:
            st.metric("macro-F1 (โมเดลจริง)", f"{b2_meta['macro_f1_test']:.3f}",
                      delta=f"{b2_meta['macro_f1_test'] - b2_meta['baseline_macro_f1']:+.3f} vs baseline")
            n_mismatch = 0 if b2_mismatch is None else len(b2_mismatch)
            st.metric("รีวิวที่ดาวไม่ตรงข้อความ (test set)", f"{n_mismatch:,}")
        with colb4:
            st.plotly_chart(
                charts.b2_f1_comparison(b2_meta["baseline_macro_f1"], b2_meta["macro_f1_test"]),
                width="stretch",
            )
        if b2_mismatch is not None and not b2_mismatch.empty:
            with st.expander(f"ดูตัวอย่างรีวิวที่ดาวไม่ตรงข้อความ ({len(b2_mismatch)} แถว)"):
                st.dataframe(
                    b2_mismatch[["category", "rating", "mismatch_type", "p_negative", "p_positive", "text_full"]],
                    hide_index=True, width="stretch",
                )

    st.divider()

    # ── B3: Clustering ──────────────────────────────────────────────────────────────────────
    st.subheader("B3 — สินค้าแบ่งได้กี่กลุ่มตามลักษณะ performance? (Clustering)")
    st.caption("ไม่รู้ล่วงหน้าว่ามีกี่กลุ่ม — ให้ K-Means หาโครงสร้างเองจากข้อมูล แทนการตั้งกฎเอง")
    b3_profile = dl.load_model_output("b3_cluster_profile.csv")
    if b3_profile is None:
        st.info("ยังไม่มีผลลัพธ์ B3 — รัน `model/model.ipynb` ก่อน")
    else:
        colb5, colb6 = st.columns([3, 2])
        with colb5:
            st.plotly_chart(charts.b3_cluster_bubble(b3_profile), width="stretch")
        with colb6:
            st.plotly_chart(charts.b3_cluster_size(b3_profile), width="stretch")

        sel_cluster = st.selectbox("🔍 เลือกกลุ่มเพื่อดูตัวอย่างสินค้าจริง", b3_profile.cluster_name.tolist())
        sample = dl.get_products_in_cluster(sel_cluster, CATS)
        if sample.empty:
            st.caption("ไม่มีสินค้าตัวอย่างในกลุ่มนี้ภายใต้หมวดที่เลือกไว้")
        else:
            st.dataframe(sample, hide_index=True, width="stretch")

    st.divider()

    # ── B4: Topic modeling ──────────────────────────────────────────────────────────────────
    st.subheader("B4 — ลูกค้าบ่นเรื่องอะไรบ้าง? (Topic Modeling)")
    st.caption("รู้ว่ารีวิว 1-2 ดาวคือ 'ไม่พอใจ' แต่ไม่รู้ว่าเรื่องอะไร มีเป็นแสนรีวิว อ่านเองไม่ไหว")
    topic_words = dl.load_model_output("b4_topic_words.csv")
    cat_share = dl.load_model_output("b4_category_topic_share.csv")
    year_share = dl.load_model_output("b4_yearly_topic_share.csv")
    if topic_words is None or cat_share is None:
        st.info("ยังไม่มีผลลัพธ์ B4 — รัน `model/model.ipynb` ก่อน")
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

        with st.expander("คำเด่นของแต่ละ topic (top 8 คำ)"):
            top8 = (topic_words[topic_words["rank"] <= 8]
                   .groupby("topic_id")["word"].apply(lambda s: ", ".join(s)).reset_index())
            top8.columns = ["Topic", "คำเด่น"]
            top8["Topic"] = top8["Topic"].map(lambda t: topic_labels.get(str(t), f"T{t}"))
            st.dataframe(top8, hide_index=True, width="stretch")

    st.divider()

    # ── B5: Anomaly detection ───────────────────────────────────────────────────────────────
    st.subheader("B5 — รีวิวไหนน่าสงสัยว่าเป็นรีวิวปลอม/รีวิวจ้าง? (Anomaly Detection)")
    st.caption(
        "ไม่มี label ว่ารีวิวไหนปลอมจริง — ผลลัพธ์คือ **'น่าสงสัย' ไม่ใช่ 'ปลอมแน่นอน'** "
        "ใช้คัดกรองเบื้องต้นแล้วให้คนตรวจซ้ำเท่านั้น"
    )
    b5_candidates = dl.load_model_output("b5_anomaly_candidates.csv")
    b5_impact = dl.load_model_output("b5_impact_summary.csv")
    if b5_candidates is None or b5_impact is None:
        st.info("ยังไม่มีผลลัพธ์ B5 — รัน `model/model.ipynb` ก่อน")
    else:
        n_flagged = len(b5_candidates)
        n_products = len(b5_impact)
        n_inflated = int((b5_impact.delta < 0).sum())
        n_deflated = int((b5_impact.delta > 0).sum())
        avg_abs = b5_impact.delta.abs().mean()

        colb9, colb10, colb11, colb12 = st.columns(4)
        colb9.metric("รีวิวที่ถูกตั้งข้อสงสัย", f"{n_flagged:,}")
        colb10.metric("สินค้าที่ได้รับผลกระทบ", f"{n_products:,}")
        colb11.metric("คะแนนถูก 'ดันขึ้น' (rating เกินจริง)", f"{n_inflated} ชิ้น")
        colb12.metric("ผลกระทบเฉลี่ยต่อคะแนน", f"±{avg_abs:.3f} ดาว")

        st.plotly_chart(charts.b5_impact_bar(b5_impact), width="stretch")

        with st.expander(f"รีวิวที่น่าสงสัยที่สุด — ลองแท็กด้วยตัวเอง (ไม่บันทึกถาวร แค่สาธิตขั้นตอนตรวจด้วยคน)"):
            show_cols = ["review_id", "category", "rating", "anomaly_score", "verified_purchase",
                        "reviewer_segment", "near_dup_similarity", "text_full", "is_fake_manual_label"]
            edited = st.data_editor(
                b5_candidates[show_cols].head(30),
                hide_index=True, width="stretch",
                disabled=[c for c in show_cols if c != "is_fake_manual_label"],
                column_config={
                    "is_fake_manual_label": st.column_config.SelectboxColumn(
                        "ผลตรวจด้วยคน", options=["", "fake", "genuine", "ไม่แน่ใจ"]
                    )
                },
            )

# ═══════════════════════════════════════ TAB: INSIGHTS ════════════════════════════════════════
with tab_insight:
    st.markdown("### 💡 Insights & ข้อเสนอแนะทางธุรกิจ")
    st.caption("คำนวณสดจากข้อมูลภายใต้ filter ปัจจุบัน — เปลี่ยน filter ด้านซ้ายแล้วตัวเลขจะอัปเดตตาม")

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
            "1. คะแนนรวมถูกครอบงำโดยผู้รีวิวครั้งเดียว",
            f"{oneoff_share:.0%} ของรีวิวมาจากคนที่รีวิวครั้งเดียวจบ (One-off) และกลุ่มนี้มีสัดส่วนให้คะแนน "
            f"1 หรือ 5 ดาวสุดขั้ว {oneoff_pol:.0%} เทียบกับขาประจำ (Power reviewer) ที่ {power_pol:.0%}"
            if power_pol is not None else "",
            "เวลารายงานคะแนนเฉลี่ยสินค้า ควรกำกับฐานผู้รีวิวเสมอ และใช้กลุ่ม One-off + not verified "
            "เป็นจุดเริ่มต้นของการตรวจรีวิวปลอม (ดูแท็บ Model Insights B5)",
        ))

    if not bias2.empty:
        unk = bias2.set_index("grp")
        if "รู้ราคา" in unk.index and "ไม่รู้ราคา" in unk.index:
            gap2 = unk.loc["รู้ราคา", "avg_rating"] - unk.loc["ไม่รู้ราคา", "avg_rating"]
            unk_pct = unk.loc["ไม่รู้ราคา", "pct"]
            insights.append((
                "2. ข้อมูลราคาขาดหายแบบไม่สุ่ม (MNAR) — บิดผลวิเคราะห์ราคา",
                f"ราคาไม่ทราบใน {unk_pct:.0f}% ของรีวิว และสินค้าที่รู้ราคามีคะแนนเฉลี่ยสูงกว่ากลุ่มที่ไม่รู้ราคา "
                f"อยู่ {gap2:+.2f} ดาว",
                "ทุกครั้งที่วิเคราะห์เรื่องราคา (เช่น price_band vs rating) ต้องรายงานว่ากรองรีวิวออกไปกี่ % "
                "และห้ามเอาข้อสรุปไปอ้างกับสินค้าทั้งหมด",
            ))

    if not imgs2.empty:
        piv = imgs2.pivot(index="category", columns="has_images", values="share_any_vote")
        if True in piv.columns and False in piv.columns:
            uplift = (piv[True] - piv[False]).mean()
            insights.append((
                "3. รีวิวที่แนบรูปได้รับความเชื่อถือมากกว่าอย่างชัดเจน",
                f"สัดส่วนรีวิวที่ได้อย่างน้อย 1 helpful vote สูงกว่าเฉลี่ย {uplift:+.1%} เมื่อมีรูปแนบ "
                "แต่รีวิวที่มีรูปมีอยู่แค่ ~6% ของรีวิวทั้งหมด",
                "ออกแบบ UX ให้แนบรูปง่ายขึ้น (เช่น ปุ่มแนบรูปที่เห็นชัด) หรือให้ incentive "
                "(คูปอง/แต้มสะสม) กับรีวิวที่มีรูป เพื่อเพิ่มสัดส่วนรีวิวคุณภาพสูง",
            ))

    b1i = dl.load_model_output("b1_regression_metrics.json")
    if b1i is not None:
        best = b1i.loc[b1i.MAE.idxmin()]
        baseline = b1i[b1i.model.str.contains("Baseline")].iloc[0]
        if best["model"] == baseline["model"]:
            insights.append((
                "4. ทำนายคะแนนสินค้าใหม่จากราคา/แบรนด์/หมวดเพียงอย่างเดียวไม่ได้ผล",
                "โมเดล Regression (Ridge, GradientBoosting) ไม่มีตัวไหนชนะ baseline (ทายค่าเฉลี่ยของหมวด) เลย",
                "อย่าใช้ราคา/แบรนด์คัดกรองสินค้าใหม่ก่อนรับเข้าขาย ควรลงทุนเก็บ feature จากคำอธิบายสินค้า "
                "หรือรอสะสมรีวิวจริงจำนวนหนึ่งก่อนประเมิน",
            ))

    b5i_impact = dl.load_model_output("b5_impact_summary.csv")
    b5i_cand = dl.load_model_output("b5_anomaly_candidates.csv")
    if b5i_impact is not None and b5i_cand is not None:
        n_inflated2 = int((b5i_impact.delta < 0).sum())
        insights.append((
            "5. พบสินค้าที่คะแนนอาจถูก 'ดันขึ้น' ด้วยรีวิวน่าสงสัย",
            f"จาก 100 รีวิวที่โมเดล Anomaly Detection ชี้ว่าน่าสงสัยที่สุด มี {len(b5i_impact)} สินค้าได้รับผลกระทบ "
            f"และ {n_inflated2} ชิ้นในนั้น คะแนนจะ **ลดลง** ถ้าตัดรีวิวน่าสงสัยออก (แปลว่าอาจถูกดันคะแนนขึ้น)",
            "ส่งรายชื่อสินค้ากลุ่มนี้ให้ทีม Trust & Safety ตรวจสอบก่อน — ผลลัพธ์เป็นแค่ 'น่าสงสัย' "
            "ห้ามลงโทษผู้ใช้จากคะแนนนี้โดยตรง ต้องมีคนตรวจซ้ำเสมอ",
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
            "6. แต่ละหมวดมีปัญหาเด่นต่างกันชัดเจน",
            " | ".join(lines),
            "ส่งหัวข้อที่พบบ่อยที่สุดของแต่ละหมวดให้ทีมพัฒนาสินค้า/ทีมเขียนรายละเอียดสินค้าแก้ตรงจุด "
            "แทนการแก้ปัญหาแบบเหมารวมทั้งพอร์ต",
        ))

    insights.append((
        "7. อย่าตีความปริมาณรีวิวปี 2022–2023 ว่าดีมานด์กำลังหด",
        "จำนวนรีวิวร่วงจาก ~468K (2021) เหลือ ~58K (2023) ซึ่งเป็นข้อจำกัดของการเก็บข้อมูลต้นทาง "
        "(เก็บถึงแค่ ก.ย. 2023) ไม่ใช่ความสนใจของลูกค้าที่ลดลงจริง",
        "รายงานแนวโน้มด้วยคะแนนเฉลี่ยแทนจำนวนรีวิวเมื่อพูดถึงปี 2022 เป็นต้นไป และตัดปีที่ข้อมูลไม่ครบ "
        "ออกจากกราฟเปรียบเทียบเชิงปริมาณ",
    ))

    for title, finding, rec in insights:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            if finding:
                st.write(finding)
            st.markdown(f"➡️ **ข้อเสนอแนะ:** {rec}")

# ═══════════════════════════════════════ TAB: CAVEATS ══════════════════════════════════════════
with tab_caveat:
    st.markdown("### ⚠️ ข้อจำกัดของข้อมูลที่ต้องรู้ก่อนใช้ dashboard นี้")
    st.markdown("""
- **ไม่มีข้อมูลยอดขาย** — จำนวนรีวิวเป็นตัวแทนคร่าว ๆ ของดีมานด์เท่านั้น ห้ามสรุปเป็นรายได้หรือส่วนแบ่งตลาด
- **Selection bias** — มีแต่คนที่เลือกจะรีวิว คนพอใจมาก/ไม่พอใจมากมีแนวโน้มรีวิวมากกว่าคนเฉย ๆ
  คะแนนเฉลี่ยจึงสูงกว่าความพึงพอใจจริงของคนซื้อทั้งหมด
- **ราคาขาดหาย ~79% ของรีวิว แบบไม่สุ่ม (MNAR)** — ดูรายละเอียดที่แท็บ Analytics คำถาม Q3
- **ปริมาณรีวิวปี 2022 เป็นต้นไปเก็บไม่ครบ** — ชุดข้อมูลต้นทางเก็บถึง ก.ย. 2023 เท่านั้น
- **`dim_user` คำนวณจาก 3 หมวดนี้เท่านั้น** ไม่ใช่ประวัติการซื้อขายทั้งหมดของผู้ใช้บน Amazon
- **B1 (regression)** อ้างได้เฉพาะสินค้าที่รู้ราคา (~21% ของรีวิว) ซึ่งคะแนนสูงกว่าค่าเฉลี่ยอยู่แล้ว
- **B2 มี distribution shift** — สัดส่วนรีวิวเชิงลบใน test สูงกว่า train ตามธรรมชาติของข้อมูล
- **B4 (topic modeling)** — ชื่อ topic มาจากคำเด่นอัตโนมัติ ควรอ่านตัวอย่างรีวิวจริงประกอบก่อนสรุป
- **B5 (anomaly detection) ให้ผลเป็น "น่าสงสัย" ไม่ใช่ "ปลอมแน่นอน"** — ไม่มี label ยืนยัน
  ห้ามเอาไปลงโทษผู้ใช้ ใช้คัดกรองเบื้องต้นแล้วให้คนตรวจซ้ำเท่านั้น
    """)
    st.caption(
        "รายละเอียดเชิงลึกทั้งหมด: `docs/business_questions.md` · "
        "`analytics/Answer_Analytic.ipynb` · `model/model.ipynb`"
    )
