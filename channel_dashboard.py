"""채널 × AppsFlyer 퍼포먼스 마케팅 대시보드
탭 1: 어제 성과 스냅샷
탭 2: 소재 리더보드
"""
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="퍼마 대시보드",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp { background-color: #EFF1FB; }
[data-testid="stSidebar"] { display: none; }

.filter-bar {
    background: #FFFFFF; border: 1px solid #C9CEEA;
    border-radius: 14px; padding: 16px 24px 10px;
    margin-bottom: 20px; box-shadow: 0 2px 10px rgba(107,116,200,0.08);
}
.section-card {
    background: #FFFFFF; border: 1px solid #D4D8F0;
    border-radius: 14px; padding: 20px 24px;
    margin-bottom: 20px; box-shadow: 0 2px 10px rgba(107,116,200,0.07);
}
.section-title {
    font-size: 1.0rem; font-weight: 700; color: #2E3670;
    margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 2px solid #E2E6F5;
}
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #D4D8F0;
    border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(107,116,200,0.10);
}
[data-testid="stMetricLabel"]  { color: #5058A0 !important; font-size: 0.88rem !important; font-weight: 700 !important; }
[data-testid="stMetricValue"]  { color: #1E2340 !important; font-size: 1.5rem !important; font-weight: 800 !important; }
[data-testid="stTabs"] [role="tab"] { font-size: 0.96rem; font-weight: 600; color: #5058A0; padding: 8px 18px; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #6B74C8; border-bottom: 3px solid #6B74C8; }
h1 { color: #2E3670 !important; }
h2, h3 { color: #2E3670 !important; }
label { color: #2E3670 !important; font-weight: 600 !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)


# ── 상수 ──────────────────────────────────────────────────────────────────────

BASE   = Path(__file__).resolve().parent
CH_PAT = str(BASE / "raw/channel/*.csv")
AF_PAT = str(BASE / "raw/appsflyer/*.csv")

CHANNEL_COLOR = {"구글": "#4285F4", "메타": "#1877F2", "네이버": "#03C75A"}
ROAS_GOOD, ROAS_BAD = 4.0, 2.0

MEDIA_MAP = {
    "googleadwords_int": "구글",
    "Facebook Ads":      "메타",
    "naver_search":      "네이버",
}


# ── 데이터 로드 ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load(ch_pat: str, af_pat: str) -> tuple[pd.DataFrame, str, str]:
    con = duckdb.connect()
    con.execute(f"CREATE TABLE ch AS SELECT * FROM read_csv_auto('{ch_pat}', union_by_name=true)")
    con.execute(f"""
        CREATE TABLE af AS
        SELECT *,
            CASE 미디어소스
                WHEN 'googleadwords_int' THEN '구글'
                WHEN 'Facebook Ads'      THEN '메타'
                WHEN 'naver_search'      THEN '네이버'
            END AS 채널
        FROM read_csv_auto('{af_pat}', union_by_name=true)
    """)
    latest, prev = con.execute("SELECT MAX(일)::DATE, (MAX(일) - INTERVAL 1 DAY)::DATE FROM ch").fetchone()
    df = con.execute("""
        SELECT
            ch.일::DATE AS 일, ch.채널, ch.채널분류, ch.캠페인, ch.캠페인목적,
            ch.그룹, ch.소재,
            ch.노출, ch.클릭 AS 클릭_ch, ch.비용,
            af.클릭      AS 클릭_af,
            af.회원가입   AS 회원가입_af,
            af.구매       AS 구매_af,
            af.구매매출   AS 구매매출_af,
            ROUND(af.구매매출 / NULLIF(ch.비용, 0), 2)              AS ROAS,
            ROUND(ch.클릭  / NULLIF(ch.노출, 0) * 100, 3)           AS CTR,
            ROUND(ch.비용  / NULLIF(af.구매_af, 0), 0)              AS CPA
        FROM ch
        LEFT JOIN af
            ON  ch.일      = af.일
            AND ch.채널    = af.채널
            AND ch.캠페인  = af.캠페인
            AND ch.그룹    = af.그룹
            AND ch.소재    = af.소재
    """).df()
    return df, str(latest), str(prev)


# ── 소재명 파싱 ────────────────────────────────────────────────────────────────

def parse_creative(name: str) -> dict:
    parts = name.split("_")
    if len(parts) >= 5:
        return {"타입": parts[0], "카테고리": parts[1], "시즌": parts[2],
                "AB": parts[3], "버전": parts[4], "AB여부": True}
    elif len(parts) == 4:
        return {"타입": parts[0], "카테고리": parts[1], "시즌": parts[2],
                "AB": None, "버전": parts[3], "AB여부": False}
    return {"타입": parts[0], "카테고리": "-", "시즌": "-", "AB": None, "버전": "-", "AB여부": False}


# ── 공통 유틸 ──────────────────────────────────────────────────────────────────

def fmt_krw(v):
    if pd.isna(v): return "-"
    if abs(v) >= 1e8: return f"₩{v/1e8:.1f}억"
    if abs(v) >= 1e4: return f"₩{v/1e4:.0f}만"
    return f"₩{v:,.0f}"

def roas_signal(v) -> str:
    if pd.isna(v): return "⚫"
    if v >= ROAS_GOOD: return "🟢"
    if v >= ROAS_BAD:  return "🟡"
    return "🔴"

def card(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ── 데이터 로드 ────────────────────────────────────────────────────────────────

df, LATEST, PREV = load(CH_PAT, AF_PAT)

today_df = df[df["일"].astype(str) == LATEST]
prev_df  = df[df["일"].astype(str) == PREV]


# ── 헤더 ──────────────────────────────────────────────────────────────────────

st.markdown("## 📡 퍼포먼스 마케팅 대시보드")
st.markdown(
    f'<div style="font-size:0.88rem;color:#5058A0;margin-bottom:16px;">'
    f'기준일: <b>{LATEST}</b> (전일: {PREV}) &nbsp;|&nbsp; '
    f'전체 데이터: {df["일"].min()} ~ {df["일"].max()}'
    f'</div>',
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["📅  어제 성과 스냅샷", "🎨  소재 리더보드"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1: 어제 성과 스냅샷
# ════════════════════════════════════════════════════════════════════════════════
with tab1:

    # 채널별 집계
    def agg_by_channel(src: pd.DataFrame) -> pd.DataFrame:
        g = src.groupby("채널", observed=True).agg(
            광고비=("비용", "sum"),
            노출=("노출", "sum"),
            클릭_ch=("클릭_ch", "sum"),
            구매매출=("구매매출_af", "sum"),
        ).reset_index()
        g["ROAS"] = (g["구매매출"] / g["광고비"].replace(0, pd.NA)).round(2)
        g["CTR"]  = (g["클릭_ch"] / g["노출"].replace(0, pd.NA) * 100).round(3)
        return g

    today_ch = agg_by_channel(today_df)
    prev_ch  = agg_by_channel(prev_df)
    merged_ch = today_ch.merge(prev_ch, on="채널", suffixes=("", "_prev"), how="left")

    # ── 전체 합계 KPI ────────────────────────────────────────────────────────
    with st.container(border=True):
        card(f"📊 전체 합계 — {LATEST}")
        tot_비용  = today_ch["광고비"].sum()
        tot_매출  = today_ch["구매매출"].sum()
        tot_roas  = round(tot_매출 / tot_비용, 2) if tot_비용 else None
        tot_ctr   = round(today_ch["클릭_ch"].sum() / today_ch["노출"].sum() * 100, 3)

        prev_비용 = prev_ch["광고비"].sum()
        prev_매출 = prev_ch["구매매출"].sum()
        prev_roas = round(prev_매출 / prev_비용, 2) if prev_비용 else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 광고비",  fmt_krw(tot_비용),
                  delta=f"{(tot_비용-prev_비용)/prev_비용*100:+.1f}%" if prev_비용 else None)
        c2.metric("총 구매매출", fmt_krw(tot_매출),
                  delta=f"{(tot_매출-prev_매출)/prev_매출*100:+.1f}%" if prev_매출 else None)
        c3.metric(f"전체 ROAS {roas_signal(tot_roas)}", str(tot_roas) if tot_roas else "-",
                  delta=f"{tot_roas-prev_roas:+.2f}" if (tot_roas and prev_roas) else None)
        c4.metric("전체 CTR", f"{tot_ctr}%")

    # ── 채널별 성과 카드 ─────────────────────────────────────────────────────
    with st.container(border=True):
        card(f"📡 채널별 성과 — {LATEST} vs {PREV}")

        cols = st.columns(len(merged_ch))
        for col, (_, row) in zip(cols, merged_ch.iterrows()):
            roas_now  = row["ROAS"]
            roas_prev = row.get("ROAS_prev", None)
            delta_roas = f"{roas_now - roas_prev:+.2f}" if pd.notna(roas_prev) else None

            delta_비용_pct = None
            if pd.notna(row.get("광고비_prev")) and row["광고비_prev"] > 0:
                delta_비용_pct = f"{(row['광고비']-row['광고비_prev'])/row['광고비_prev']*100:+.1f}%"

            with col:
                st.markdown(
                    f"<div style='text-align:center;font-size:1.05rem;font-weight:700;"
                    f"color:{CHANNEL_COLOR.get(row['채널'],'#888')};margin-bottom:8px;'>"
                    f"{roas_signal(roas_now)} {row['채널']}</div>",
                    unsafe_allow_html=True,
                )
                st.metric("광고비",  fmt_krw(row["광고비"]),  delta=delta_비용_pct)
                st.metric("ROAS",    str(roas_now),           delta=delta_roas,
                          delta_color="normal")
                st.metric("CTR",     f"{row['CTR']}%")
                st.metric("구매매출", fmt_krw(row["구매매출"]))

    # ── 채널별 광고비 vs ROAS 바차트 ─────────────────────────────────────────
    with st.container(border=True):
        card("채널별 광고비 · ROAS 비교")
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(today_ch, x="채널", y="광고비", color="채널",
                         color_discrete_map=CHANNEL_COLOR,
                         title="광고비", labels={"광고비": "광고비 (₩)", "채널": ""})
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig2 = px.bar(today_ch, x="채널", y="ROAS", color="채널",
                          color_discrete_map=CHANNEL_COLOR,
                          title="ROAS", labels={"ROAS": "ROAS", "채널": ""})
            fig2.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670",
                           annotation_text="양호 기준 4.0")
            fig2.add_hline(y=ROAS_BAD, line_dash="dash", line_color="#EF553B",
                           annotation_text="위험 기준 2.0")
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

    # ── 7일 ROAS 추이 ─────────────────────────────────────────────────────────
    with st.container(border=True):
        card("최근 7일 채널별 ROAS 추이")
        dates_7 = sorted(df["일"].astype(str).unique())[-7:]
        df7 = df[df["일"].astype(str).isin(dates_7)]
        trend = df7.groupby(["일", "채널"], observed=True).agg(
            비용=("비용", "sum"), 매출=("구매매출_af", "sum"),
        ).reset_index()
        trend["ROAS"] = (trend["매출"] / trend["비용"].replace(0, pd.NA)).round(2)
        trend["일"] = trend["일"].astype(str)

        fig3 = px.line(trend, x="일", y="ROAS", color="채널",
                       color_discrete_map=CHANNEL_COLOR, markers=True,
                       labels={"일": "", "ROAS": "ROAS"})
        fig3.add_hline(y=ROAS_GOOD, line_dash="dot", line_color="#6B74C8",
                       annotation_text="기준 4.0")
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2: 소재 리더보드
# ════════════════════════════════════════════════════════════════════════════════
with tab2:

    # 소재 집계 (전체 기간)
    creative_grp = df.groupby(["소재", "채널"], observed=True).agg(
        광고비=("비용", "sum"),
        노출=("노출", "sum"),
        클릭_ch=("클릭_ch", "sum"),
        구매매출=("구매매출_af", "sum"),
        구매=("구매_af", "sum"),
    ).reset_index()
    creative_grp["ROAS"] = (creative_grp["구매매출"] / creative_grp["광고비"].replace(0, pd.NA)).round(2)
    creative_grp["CTR"]  = (creative_grp["클릭_ch"] / creative_grp["노출"].replace(0, pd.NA) * 100).round(3)

    # 소재명 파싱
    parsed = creative_grp["소재"].apply(parse_creative).apply(pd.Series)
    creative_grp = pd.concat([creative_grp, parsed], axis=1)

    # ── 기간 필터 ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("🔍 필터")
        f1, f2, f3 = st.columns(3)
        sel_ch  = f1.multiselect("채널", df["채널"].unique().tolist(),
                                 default=df["채널"].unique().tolist(), key="cr_ch")
        sel_typ = f2.multiselect("소재 타입", sorted(creative_grp["타입"].unique().tolist()),
                                 default=sorted(creative_grp["타입"].unique().tolist()), key="cr_typ")
        sel_cat = f3.multiselect("카테고리", sorted(creative_grp["카테고리"].unique().tolist()),
                                 default=sorted(creative_grp["카테고리"].unique().tolist()), key="cr_cat")

    cr = creative_grp[
        creative_grp["채널"].isin(sel_ch) &
        creative_grp["타입"].isin(sel_typ) &
        creative_grp["카테고리"].isin(sel_cat)
    ].dropna(subset=["ROAS"]).copy()

    # ── Top 5 / Bottom 5 ──────────────────────────────────────────────────────
    with st.container(border=True):
        card("🏆 ROAS Top 5 / Bottom 5")

        top5    = cr.nlargest(5, "ROAS")[["소재","채널","타입","카테고리","AB","광고비","ROAS","CTR"]]
        bottom5 = cr.nsmallest(5, "ROAS")[["소재","채널","타입","카테고리","AB","광고비","ROAS","CTR"]]

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**🟢 Top 5**")
            t = top5.copy()
            t["광고비"] = t["광고비"].apply(fmt_krw)
            t["CTR"]   = t["CTR"].apply(lambda x: f"{x}%")
            t["AB"]    = t["AB"].fillna("-")
            st.dataframe(t, use_container_width=True, hide_index=True)
        with col_r:
            st.markdown("**🔴 Bottom 5**")
            b = bottom5.copy()
            b["광고비"] = b["광고비"].apply(fmt_krw)
            b["CTR"]   = b["CTR"].apply(lambda x: f"{x}%")
            b["AB"]    = b["AB"].fillna("-")
            st.dataframe(b, use_container_width=True, hide_index=True)

    # ── 소재 타입별 평균 성과 ─────────────────────────────────────────────────
    with st.container(border=True):
        card("소재 타입별 평균 성과 (VID / IMG / CRS / TXT)")
        TYPE_COLOR = {"VID": "#6B74C8", "IMG": "#EF553B", "CRS": "#00CC96", "TXT": "#FFA500"}

        type_grp = cr.groupby("타입", observed=True).agg(
            광고비=("광고비", "sum"), 구매매출=("구매매출", "sum"), CTR=("CTR", "mean"),
        ).reset_index()
        type_grp["ROAS"] = (type_grp["구매매출"] / type_grp["광고비"].replace(0, pd.NA)).round(2)

        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(type_grp, x="타입", y="ROAS", color="타입",
                         color_discrete_map=TYPE_COLOR, title="타입별 ROAS",
                         labels={"타입": "", "ROAS": "ROAS"})
            fig.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670",
                          annotation_text="기준 4.0")
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig2 = px.bar(type_grp, x="타입", y="CTR", color="타입",
                          color_discrete_map=TYPE_COLOR, title="타입별 평균 CTR (%)",
                          labels={"타입": "", "CTR": "CTR (%)"})
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

    # ── A/B 테스트 비교 ───────────────────────────────────────────────────────
    with st.container(border=True):
        card("🧪 A/B 테스트 소재 비교")

        ab_cr = cr[cr["AB여부"]].copy()
        ab_cr["소재_base"] = ab_cr["소재"].apply(
            lambda x: "_".join(x.split("_")[:3] + x.split("_")[4:])  # AB 제거한 기본 소재명
        )

        if ab_cr.empty:
            st.info("현재 필터 조건에 A/B 테스트 소재가 없습니다.")
        else:
            pivot = ab_cr.groupby(["소재_base", "AB", "채널"], observed=True).agg(
                ROAS=("ROAS", "mean"), CTR=("CTR", "mean"), 광고비=("광고비", "sum"),
            ).reset_index()

            ab_wide = pivot.pivot_table(
                index=["소재_base", "채널"], columns="AB",
                values=["ROAS", "CTR"], aggfunc="mean"
            ).round(3).reset_index()
            ab_wide.columns = [
                "_".join(c).strip("_") if c[1] else c[0]
                for c in ab_wide.columns
            ]
            ab_wide = ab_wide.rename(columns={"소재_base": "소재(공통)", "채널": "채널"})

            if "ROAS_A" in ab_wide.columns and "ROAS_B" in ab_wide.columns:
                ab_wide["승자"] = ab_wide.apply(
                    lambda r: "🅰️ A 우세" if r["ROAS_A"] > r["ROAS_B"] else "🅱️ B 우세", axis=1
                )

            st.dataframe(ab_wide, use_container_width=True, hide_index=True)

            # A vs B ROAS 시각화
            fig_ab = px.bar(
                pivot[pivot["AB"].isin(["A", "B"])],
                x="소재_base", y="ROAS", color="AB",
                barmode="group", facet_col="채널",
                color_discrete_map={"A": "#6B74C8", "B": "#EF553B"},
                title="소재별 A vs B ROAS 비교",
                labels={"소재_base": "소재", "ROAS": "ROAS"},
            )
            fig_ab.update_xaxes(tickangle=30)
            fig_ab.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)",
                                 plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ab, use_container_width=True)
