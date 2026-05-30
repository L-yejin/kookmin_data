"""마케팅 데이터 EDA 대시보드
채널 × AppsFlyer 데이터를 자동 로딩·조인하고 Streamlit으로 시각화.
새 날짜 파일(YYYY-MM-DD_channel.csv / YYYY-MM-DD_appsflyer.csv)을 이 폴더에 추가하면
페이지 새로고침 시 자동 반영됨.
"""
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="마케팅 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent

CHANNEL_MAP = {
    "구글": "googleadwords_int",
    "메타": "Facebook Ads",
    "네이버": "naver_search",
}
CHANNEL_COLOR = {
    "구글": "#4285F4",
    "메타": "#1877F2",
    "네이버": "#03C75A",
}
ROAS_GOOD = 4.0
ROAS_BAD = 2.0


# ── 데이터 로딩 & 조인 ────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    ch_files = sorted(BASE.glob("*_channel.csv"))
    af_files = sorted(BASE.glob("*_appsflyer.csv"))
    if not ch_files or not af_files:
        return pd.DataFrame()

    ch_pat = str(BASE / "*_channel.csv")
    af_pat = str(BASE / "*_appsflyer.csv")

    con = duckdb.connect()
    con.execute(f"CREATE TABLE ch AS SELECT * FROM read_csv_auto('{ch_pat}')")
    con.execute(f"CREATE TABLE af AS SELECT * FROM read_csv_auto('{af_pat}')")

    pairs = ", ".join(f"('{k}', '{v}')" for k, v in CHANNEL_MAP.items())
    con.execute(f"CREATE TABLE cmap(채널 VARCHAR, 미디어소스 VARCHAR); INSERT INTO cmap VALUES {pairs}")

    df = con.execute("""
        SELECT
            ch.일,
            ch.채널,
            ch.채널분류,
            ch.캠페인,
            ch.캠페인목적,
            ch.그룹,
            ch.소재,
            ch.노출,
            ch.클릭          AS ch_클릭,
            ch.비용,
            ch.회원가입      AS ch_회원가입,
            ch.구매          AS ch_구매,
            ch.구매매출      AS ch_구매매출,
            COALESCE(af.클릭,    0) AS af_클릭,
            COALESCE(af.회원가입,0) AS af_회원가입,
            COALESCE(af.구매,    0) AS af_구매,
            COALESCE(af.구매매출,0) AS af_구매매출
        FROM ch
        LEFT JOIN cmap ON ch.채널 = cmap.채널
        LEFT JOIN af
            ON  ch.일         = af.일
            AND cmap.미디어소스 = af.미디어소스
            AND ch.캠페인     = af.캠페인
            AND ch.그룹       = af.그룹
            AND ch.소재       = af.소재
    """).df()
    con.close()

    df["일"] = pd.to_datetime(df["일"])
    df["CTR"]  = (df["ch_클릭"]   / df["노출"].replace(0, float("nan"))        * 100).round(2)
    df["CPC"]  = (df["비용"]      / df["ch_클릭"].replace(0, float("nan"))           ).round(0)
    df["ROAS"] = (df["af_구매매출"] / df["비용"].replace(0, float("nan"))             ).round(2)
    df["CAC"]  = (df["비용"]      / df["af_회원가입"].replace(0, float("nan"))        ).round(0)
    df["CVR"]  = (df["af_구매"]   / df["af_클릭"].replace(0, float("nan"))    * 100).round(2)
    return df


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def fmt_won(v: float) -> str:
    if pd.isna(v):
        return "-"
    if v >= 1e8:
        return f"₩{v/1e8:.1f}억"
    if v >= 1e4:
        return f"₩{v/1e4:.0f}만"
    return f"₩{v:,.0f}"


def roas_status(v) -> str:
    if pd.isna(v):
        return "데이터없음"
    if v >= ROAS_GOOD:
        return "🟢 양호"
    if v >= ROAS_BAD:
        return "🟡 관찰"
    return "🔴 개선필요"


# ── 로딩 ─────────────────────────────────────────────────────────────────────

df_raw = load_data()

if df_raw.empty:
    st.error(
        "데이터 파일을 찾을 수 없습니다.\n\n"
        "`YYYY-MM-DD_channel.csv` / `YYYY-MM-DD_appsflyer.csv` 파일을 "
        "이 스크립트와 같은 폴더에 넣어주세요."
    )
    st.stop()

# ── 사이드바 필터 ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("필터")

    date_min = df_raw["일"].min().date()
    date_max = df_raw["일"].max().date()
    d_from, d_to = st.date_input(
        "기간", value=(date_min, date_max),
        min_value=date_min, max_value=date_max,
    )

    sel_ch = st.multiselect(
        "채널", sorted(df_raw["채널"].unique()),
        default=sorted(df_raw["채널"].unique()),
    )
    sel_pur = st.multiselect(
        "캠페인 목적", sorted(df_raw["캠페인목적"].unique()),
        default=sorted(df_raw["캠페인목적"].unique()),
    )

    st.divider()
    exclude_brand = st.toggle("브랜드·일반KW 제외", value=True,
                              help="ROAS 부풀림 방지를 위해 브랜드/일반KW 캠페인 제외")

    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ── 필터 적용 ─────────────────────────────────────────────────────────────────

df = df_raw.copy()
df = df[(df["일"].dt.date >= d_from) & (df["일"].dt.date <= d_to)]
df = df[df["채널"].isin(sel_ch)]
df = df[df["캠페인목적"].isin(sel_pur)]
if exclude_brand:
    df = df[~df["캠페인목적"].isin(["브랜드KW", "일반KW"])]

if df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

file_count = len(sorted(BASE.glob("*_channel.csv")))
st.caption(f"로드된 날짜 파일: {file_count}개 | 필터 적용 후 행 수: {len(df):,}행")

# ── 탭 ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📺 채널별", "🎯 캠페인 랭킹", "🔍 Raw 데이터"])

# =============================================================================
# TAB 1 ── Overview
# =============================================================================
with tab1:
    tot_cost  = df["비용"].sum()
    tot_rev   = df["af_구매매출"].sum()
    tot_roas  = tot_rev / tot_cost if tot_cost else 0
    tot_joins = df["af_회원가입"].sum()
    tot_cac   = tot_cost / tot_joins if tot_joins else float("nan")
    tot_impr  = df["노출"].sum()
    tot_click = df["ch_클릭"].sum()
    tot_ctr   = tot_click / tot_impr * 100 if tot_impr else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 광고비",       fmt_won(tot_cost))
    c2.metric("AF 구매매출",     fmt_won(tot_rev))
    c3.metric("ROAS (AF기준)",   f"{tot_roas:.2f}")
    c4.metric("CAC (원/가입)",   fmt_won(tot_cac))
    c5.metric("CTR",             f"{tot_ctr:.2f}%")

    st.divider()

    daily = (
        df.groupby("일")
        .agg(비용=("비용","sum"), af_구매매출=("af_구매매출","sum"),
             노출=("노출","sum"), ch_클릭=("ch_클릭","sum"),
             af_회원가입=("af_회원가입","sum"))
        .reset_index()
    )
    daily["ROAS"] = daily["af_구매매출"] / daily["비용"].replace(0, float("nan"))
    daily["CTR"]  = daily["ch_클릭"] / daily["노출"].replace(0, float("nan")) * 100

    col_l, col_r = st.columns(2)
    with col_l:
        fig = go.Figure()
        fig.add_bar(x=daily["일"], y=daily["비용"], name="광고비", marker_color="#6366F1", opacity=0.8)
        fig.add_scatter(x=daily["일"], y=daily["af_구매매출"], name="AF 매출",
                        line=dict(color="#10B981", width=2), yaxis="y2")
        fig.update_layout(
            title="일별 광고비 vs AF 매출",
            yaxis=dict(title="광고비 (원)"),
            yaxis2=dict(title="매출 (원)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.18),
            height=360, margin=dict(t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = px.line(daily, x="일", y="ROAS", title="일별 ROAS (AF 기준)",
                       markers=True)
        fig2.add_hline(y=ROAS_GOOD, line_dash="dot", line_color="#10B981",
                       annotation_text="양호 (4.0)", annotation_position="right")
        fig2.add_hline(y=ROAS_BAD,  line_dash="dot", line_color="#EF4444",
                       annotation_text="위험 (2.0)", annotation_position="right")
        fig2.update_traces(line_color="#6366F1")
        fig2.update_layout(height=360, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        fig3 = px.bar(daily, x="일", y="af_회원가입", title="일별 AF 회원가입",
                      color_discrete_sequence=["#8B5CF6"])
        fig3.update_layout(height=300, margin=dict(t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        fig4 = px.line(daily, x="일", y="CTR", title="일별 CTR (%)", markers=True,
                       color_discrete_sequence=["#F59E0B"])
        fig4.update_layout(height=300, margin=dict(t=40, b=10))
        st.plotly_chart(fig4, use_container_width=True)


# =============================================================================
# TAB 2 ── 채널별
# =============================================================================
with tab2:
    ch_agg = (
        df.groupby("채널")
        .agg(비용=("비용","sum"), 노출=("노출","sum"), ch_클릭=("ch_클릭","sum"),
             af_회원가입=("af_회원가입","sum"), af_구매=("af_구매","sum"),
             af_구매매출=("af_구매매출","sum"))
        .reset_index()
    )
    ch_agg["ROAS"] = (ch_agg["af_구매매출"] / ch_agg["비용"].replace(0, float("nan"))).round(2)
    ch_agg["CTR"]  = (ch_agg["ch_클릭"] / ch_agg["노출"].replace(0, float("nan")) * 100).round(2)
    ch_agg["CPC"]  = (ch_agg["비용"] / ch_agg["ch_클릭"].replace(0, float("nan"))).round(0)
    ch_agg["CAC"]  = (ch_agg["비용"] / ch_agg["af_회원가입"].replace(0, float("nan"))).round(0)

    col_l, col_r = st.columns(2)
    with col_l:
        fig = px.bar(ch_agg, x="채널", y="비용", title="채널별 광고비",
                     color="채널", color_discrete_map=CHANNEL_COLOR, text_auto=True)
        fig.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig = px.bar(ch_agg, x="채널", y="ROAS", title="채널별 ROAS (AF 기준)",
                     color="채널", color_discrete_map=CHANNEL_COLOR, text_auto=True)
        fig.add_hline(y=ROAS_GOOD, line_dash="dot", line_color="#10B981",
                      annotation_text="양호(4.0)")
        fig.add_hline(y=ROAS_BAD, line_dash="dot", line_color="#EF4444",
                      annotation_text="위험(2.0)")
        fig.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig, use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        fig = px.bar(ch_agg, x="채널", y="CTR", title="채널별 CTR (%)",
                     color="채널", color_discrete_map=CHANNEL_COLOR, text_auto=True)
        fig.update_layout(showlegend=False, height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_r2:
        fig = px.bar(ch_agg, x="채널", y="CAC", title="채널별 CAC (원/회원가입)",
                     color="채널", color_discrete_map=CHANNEL_COLOR, text_auto=True)
        fig.update_layout(showlegend=False, height=320)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("채널 요약")
    disp = ch_agg[["채널","비용","af_구매매출","ROAS","CTR","CPC","CAC","af_회원가입","af_구매"]].copy()
    disp.columns = ["채널","광고비","AF매출","ROAS","CTR(%)","CPC","CAC","AF가입","AF구매"]
    st.dataframe(disp.set_index("채널"), use_container_width=True)

    # 채널별 일별 추세
    st.subheader("채널별 일별 ROAS 추세")
    ch_daily = (
        df.groupby(["일","채널"])
        .agg(비용=("비용","sum"), af_구매매출=("af_구매매출","sum"))
        .reset_index()
    )
    ch_daily["ROAS"] = ch_daily["af_구매매출"] / ch_daily["비용"].replace(0, float("nan"))
    fig = px.line(ch_daily, x="일", y="ROAS", color="채널",
                  color_discrete_map=CHANNEL_COLOR, markers=True)
    fig.add_hline(y=ROAS_GOOD, line_dash="dot", line_color="#10B981")
    fig.add_hline(y=ROAS_BAD, line_dash="dot", line_color="#EF4444")
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# TAB 3 ── 캠페인 랭킹
# =============================================================================
with tab3:
    cmp_agg = (
        df.groupby(["캠페인","캠페인목적","채널"])
        .agg(비용=("비용","sum"), 노출=("노출","sum"), ch_클릭=("ch_클릭","sum"),
             af_회원가입=("af_회원가입","sum"), af_구매=("af_구매","sum"),
             af_구매매출=("af_구매매출","sum"))
        .reset_index()
    )
    cmp_agg["ROAS"] = (cmp_agg["af_구매매출"] / cmp_agg["비용"].replace(0, float("nan"))).round(2)
    cmp_agg["CTR"]  = (cmp_agg["ch_클릭"] / cmp_agg["노출"].replace(0, float("nan")) * 100).round(2)
    cmp_agg["CAC"]  = (cmp_agg["비용"] / cmp_agg["af_회원가입"].replace(0, float("nan"))).round(0)
    cmp_agg["상태"] = cmp_agg["ROAS"].apply(roas_status)

    cmp_sorted = cmp_agg.sort_values("ROAS", ascending=False).reset_index(drop=True)

    col_l, col_r = st.columns([3, 1])
    with col_l:
        chart_h = max(400, len(cmp_sorted) * 30)
        fig = px.bar(
            cmp_sorted, x="ROAS", y="캠페인", orientation="h",
            color="채널", color_discrete_map=CHANNEL_COLOR,
            title="캠페인별 ROAS 순위 (높은 순)",
            height=chart_h,
        )
        fig.add_vline(x=ROAS_GOOD, line_dash="dot", line_color="#10B981",
                      annotation_text="양호(4.0)")
        fig.add_vline(x=ROAS_BAD, line_dash="dot", line_color="#EF4444",
                      annotation_text="위험(2.0)")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("ROAS 상태")
        sc = cmp_agg["상태"].value_counts().reset_index()
        sc.columns = ["상태", "건수"]
        fig_pie = px.pie(
            sc, names="상태", values="건수",
            color="상태",
            color_discrete_map={
                "🟢 양호": "#10B981", "🟡 관찰": "#F59E0B",
                "🔴 개선필요": "#EF4444", "데이터없음": "#9CA3AF",
            },
            height=320,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("전체 캠페인 테이블")
    disp_c = cmp_sorted[["상태","채널","캠페인목적","캠페인","비용","af_구매매출","ROAS","CTR","CAC","af_회원가입","af_구매"]].copy()
    disp_c.columns = ["상태","채널","목적","캠페인","광고비","AF매출","ROAS","CTR(%)","CAC","AF가입","AF구매"]
    st.dataframe(disp_c, use_container_width=True)


# =============================================================================
# TAB 4 ── Raw 데이터
# =============================================================================
with tab4:
    st.subheader(f"조인 결과 ({len(df):,}행)")
    st.caption("채널 보고 기준(ch_*) + AppsFlyer 기준(af_*) 컬럼이 함께 표시됩니다.")

    search = st.text_input("🔍 검색 (채널·캠페인·소재 등)", "")
    df_show = df.copy()
    if search:
        mask = df_show.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False)).any(axis=1)
        df_show = df_show[mask]

    st.dataframe(df_show.reset_index(drop=True), use_container_width=True, height=500)

    csv = df_show.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드 (utf-8-sig)", csv,
        file_name="joined_data.csv", mime="text/csv",
    )
