"""핀테크 광고 데이터 EDA 대시보드
핀테크_데이터_분석_0418.xlsx (raw 시트) 기반
"""
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="핀테크 광고 대시보드",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── 전체 배경 ── */
.stApp { background-color: #EFF1FB; }
[data-testid="stSidebar"] { display: none; }

/* ── 필터 바 ── */
.filter-bar {
    background: #FFFFFF;
    border: 1px solid #C9CEEA;
    border-radius: 14px;
    padding: 18px 24px 12px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(107,116,200,0.08);
}
.filter-bar-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #6B74C8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ── 섹션 카드 ── */
.section-card {
    background: #FFFFFF;
    border: 1px solid #D4D8F0;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(107,116,200,0.07);
}
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #2E3670;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E2E6F5;
}

/* ── 메트릭 카드 ── */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D4D8F0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(107,116,200,0.10);
}
[data-testid="stMetricLabel"] {
    color: #5058A0 !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    color: #1E2340 !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
}

/* ── 탭 ── */
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.96rem;
    font-weight: 600;
    color: #5058A0;
    padding: 8px 18px;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #6B74C8;
    border-bottom: 3px solid #6B74C8;
}

/* ── 헤더 ── */
h1 { color: #2E3670 !important; font-size: 1.8rem !important; }
h2 { color: #2E3670 !important; font-size: 1.3rem !important; }
h3 { color: #3A449A !important; font-size: 1.1rem !important; }

/* ── 데이터프레임 ── */
[data-testid="stDataFrame"] th {
    background-color: #D4D8F0 !important;
    color: #1E2340 !important;
    font-weight: 700 !important;
}

/* ── 구분선 ── */
hr { border-color: #C9CEEA; margin: 18px 0; }

/* ── selectbox / multiselect 레이블 ── */
label { color: #2E3670 !important; font-weight: 600 !important; font-size: 0.85rem !important; }
</style>
""", unsafe_allow_html=True)


# ── 상수 ──────────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent
EXCEL_PATH = BASE / "핀테크_데이터_분석_0418.xlsx"

CHANNEL_COLOR = {"구글": "#4285F4", "페이스북": "#1877F2", "네이버검색": "#03C75A"}
FORMAT_COLOR  = {"이미지": "#FF6B6B", "영상": "#FFA500", "일반키워드": "#9B59B6", "브랜드키워드": "#1ABC9C"}

FUNNEL_COLS   = ["광고노출","광고클릭","앱설치","앱실행","회원가입","계좌개설","첫거래","반복사용","자동이체설정","추천완료"]
FUNNEL_LABELS = ["노출","클릭","앱설치","앱실행","회원가입","계좌개설","첫거래","반복사용","자동이체","추천완료"]


# ── 데이터 로드 ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def load_data() -> pd.DataFrame:
    df = pd.read_excel(EXCEL_PATH, sheet_name="raw")
    df["date"] = pd.to_datetime(df["date"])
    df["yearmonth"] = df["date"].dt.to_period("M").astype(str)
    df["week"]      = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["CTR"]              = df["광고클릭"] / df["광고노출"].replace(0, pd.NA)
    df["CPI"]              = df["광고비"]  / df["앱설치"].replace(0, pd.NA)
    df["CPA_회원가입"]     = df["광고비"]  / df["회원가입"].replace(0, pd.NA)
    df["CPA_계좌개설"]     = df["광고비"]  / df["계좌개설"].replace(0, pd.NA)
    df["설치전환율"]       = df["앱설치"]  / df["광고클릭"].replace(0, pd.NA)
    df["회원가입전환율"]   = df["회원가입"] / df["앱설치"].replace(0, pd.NA)
    df["계좌개설전환율"]   = df["계좌개설"] / df["회원가입"].replace(0, pd.NA)
    df["첫거래전환율"]     = df["첫거래"]  / df["계좌개설"].replace(0, pd.NA)
    return df


# ── 공통 포맷 ──────────────────────────────────────────────────────────────────

def fmt_num(v, prefix="", suffix="", decimals=0):
    if pd.isna(v): return "-"
    if abs(v) >= 1e8: return f"{prefix}{v/1e8:.1f}억{suffix}"
    if abs(v) >= 1e4: return f"{prefix}{v/1e4:.1f}만{suffix}"
    return f"{prefix}{v:,.{decimals}f}{suffix}"

def fmt_pct(v):
    return f"{v*100:.2f}%" if not pd.isna(v) else "-"

def card(title: str):
    """섹션 제목 카드 헤더를 렌더링"""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ── 데이터 전체 로드 ──────────────────────────────────────────────────────────

df_all = load_data()


# ════════════════════════════════════════════════════════════════════════════════
# 상단 헤더
# ════════════════════════════════════════════════════════════════════════════════

st.markdown("## 💳 핀테크 광고 데이터 대시보드")
st.markdown('<div style="font-size:0.9rem;color:#5058A0;margin-bottom:18px;">데이터 기간: 2025.01 ~ 2025.12 &nbsp;|&nbsp; 채널: 구글·페이스북·네이버검색</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# 상단 필터 바
# ════════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="filter-bar"><div class="filter-bar-title">🔍 필터</div>', unsafe_allow_html=True)

f1, f2, f3, f4, f5 = st.columns([2, 1.5, 1.5, 1.8, 1])

with f1:
    date_min = df_all["date"].min().date()
    date_max = df_all["date"].max().date()
    date_range = st.date_input(
        "날짜 범위",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        label_visibility="visible",
    )
with f2:
    channels = st.multiselect(
        "채널",
        options=df_all["channel"].unique().tolist(),
        default=df_all["channel"].unique().tolist(),
    )
with f3:
    objectives = st.multiselect(
        "캠페인 목적",
        options=df_all["campaign_objective"].unique().tolist(),
        default=df_all["campaign_objective"].unique().tolist(),
    )
with f4:
    formats = st.multiselect(
        "크리에이티브 포맷",
        options=df_all["creative_format"].unique().tolist(),
        default=df_all["creative_format"].unique().tolist(),
    )
with f5:
    granularity = st.radio("시계열 단위", ["월별", "주별"], horizontal=False)

st.markdown('</div>', unsafe_allow_html=True)


# ── 필터 적용 ─────────────────────────────────────────────────────────────────

if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = pd.Timestamp(date_min), pd.Timestamp(date_max)

df = df_all[
    (df_all["date"] >= start) &
    (df_all["date"] <= end) &
    (df_all["channel"].isin(channels)) &
    (df_all["campaign_objective"].isin(objectives)) &
    (df_all["creative_format"].isin(formats))
].copy()

if df.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()


# ════════════════════════════════════════════════════════════════════════════════
# 탭 구성
# ════════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📊  KPI 요약", "📈  시계열 트렌드", "📡  채널 비교", "🎨  캠페인·크리에이티브", "🔽  퍼널 분석", "🔬  통계 검정"]
)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1: KPI 요약
# ════════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── 핵심 KPI ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("핵심 성과 지표 (KPI)")

        total    = df[["광고비","광고노출","광고클릭","앱설치","회원가입","계좌개설","첫거래"]].sum()
        avg_ctr  = df["광고클릭"].sum() / df["광고노출"].sum()
        avg_cpi  = df["광고비"].sum()   / df["앱설치"].sum()
        avg_cpa_r = df["광고비"].sum()  / df["회원가입"].sum()
        avg_cpa_a = df["광고비"].sum()  / df["계좌개설"].sum()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("총 광고비",     fmt_num(total["광고비"], prefix="₩"))
        c2.metric("총 광고노출",   fmt_num(total["광고노출"]))
        c3.metric("CTR (클릭률)",  fmt_pct(avg_ctr))
        c4.metric("CPI (설치당비용)", fmt_num(avg_cpi, prefix="₩"))
        c5.metric("CPA 회원가입",  fmt_num(avg_cpa_r, prefix="₩"))

        st.markdown("<br>", unsafe_allow_html=True)
        c6, c7, c8, c9, c10 = st.columns(5)
        c6.metric("총 앱설치",   fmt_num(total["앱설치"]))
        c7.metric("총 회원가입", fmt_num(total["회원가입"]))
        c8.metric("총 계좌개설", fmt_num(total["계좌개설"]))
        c9.metric("총 첫거래",   fmt_num(total["첫거래"]))
        c10.metric("CPA 계좌개설", fmt_num(avg_cpa_a, prefix="₩"))

    # ── 채널별 KPI 테이블 ─────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널별 KPI 비교표")

        ch_grp = df.groupby("channel").agg(
            광고비=("광고비","sum"), 광고노출=("광고노출","sum"),
            광고클릭=("광고클릭","sum"), 앱설치=("앱설치","sum"),
            회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"), 첫거래=("첫거래","sum"),
        ).reset_index()
        ch_grp["CTR"]          = ch_grp["광고클릭"] / ch_grp["광고노출"]
        ch_grp["CPI"]          = ch_grp["광고비"]   / ch_grp["앱설치"]
        ch_grp["CPA_회원가입"] = ch_grp["광고비"]   / ch_grp["회원가입"]
        ch_grp["CPA_계좌개설"] = ch_grp["광고비"]   / ch_grp["계좌개설"]
        ch_grp["광고비비중"]   = ch_grp["광고비"]   / ch_grp["광고비"].sum()

        display = ch_grp.copy()
        for col in ["광고비","CPI","CPA_회원가입","CPA_계좌개설"]:
            display[col] = display[col].apply(lambda x: fmt_num(x, prefix="₩"))
        display["CTR"]      = display["CTR"].apply(fmt_pct)
        display["광고비비중"] = display["광고비비중"].apply(fmt_pct)
        display = display.rename(columns={"channel":"채널"})
        st.dataframe(
            display[["채널","광고비","광고비비중","광고노출","광고클릭","CTR","앱설치","CPI","회원가입","CPA_회원가입","계좌개설","CPA_계좌개설"]],
            use_container_width=True, hide_index=True
        )

    # ── 파이차트 ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널별 구성 비중")
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.pie(ch_grp, names="channel", values="광고비",
                         color="channel", color_discrete_map=CHANNEL_COLOR,
                         title="광고비 비중", hole=0.4)
            fig.update_traces(textposition="outside", textinfo="percent+label")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig = px.pie(ch_grp, names="channel", values="앱설치",
                         color="channel", color_discrete_map=CHANNEL_COLOR,
                         title="앱설치 비중", hole=0.4)
            fig.update_traces(textposition="outside", textinfo="percent+label")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2: 시계열 트렌드
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    time_col = "yearmonth" if granularity == "월별" else "week"

    ts = df.groupby([time_col, "channel"], observed=True).agg(
        광고비=("광고비","sum"), 광고노출=("광고노출","sum"),
        광고클릭=("광고클릭","sum"), 앱설치=("앱설치","sum"),
        회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
    ).reset_index()
    ts["CTR"] = ts["광고클릭"] / ts["광고노출"]
    ts["CPI"] = ts["광고비"]   / ts["앱설치"]
    if granularity == "주별":
        ts[time_col] = ts[time_col].astype(str)

    ts_total = df.groupby(time_col, observed=True).agg(
        광고비=("광고비","sum"), 앱설치=("앱설치","sum"),
        회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
    ).reset_index()
    if granularity == "주별":
        ts_total[time_col] = ts_total[time_col].astype(str)

    metric_options = {
        "광고비 (₩)":"광고비","광고노출":"광고노출","광고클릭":"광고클릭",
        "앱설치":"앱설치","회원가입":"회원가입","계좌개설":"계좌개설","CTR":"CTR","CPI (₩)":"CPI",
    }

    # ── 채널별 추이 ───────────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널별 지표 추이")
        sel_label  = st.selectbox("지표 선택", list(metric_options.keys()))
        sel_metric = metric_options[sel_label]
        fig = px.line(ts, x=time_col, y=sel_metric, color="channel",
                      color_discrete_map=CHANNEL_COLOR, markers=True,
                      title=f"{granularity} {sel_label} — 채널별",
                      labels={time_col:"", sel_metric:sel_label, "channel":"채널"})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # ── 전체 합계 광고비 + 전환 ───────────────────────────────────────────────
    with st.container(border=True):
        card("전체 합계 추이")
        col_l, col_r = st.columns(2)
        with col_l:
            fig2 = px.bar(ts_total, x=time_col, y="광고비",
                          title=f"{granularity} 전체 광고비",
                          color_discrete_sequence=["#6B74C8"],
                          labels={time_col:""})
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        with col_r:
            fig3 = go.Figure()
            for col_name, color in [("앱설치","#EF553B"),("회원가입","#00CC96"),("계좌개설","#AB63FA")]:
                fig3.add_trace(go.Bar(name=col_name, x=ts_total[time_col], y=ts_total[col_name]))
            fig3.update_layout(barmode="group", title=f"{granularity} 전환 지표",
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

    # ── 히트맵 ───────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("월 × 채널 광고비 히트맵")
        hm = df.groupby(["yearmonth","channel"], observed=True)["광고비"].sum().reset_index()
        hm_pivot = hm.pivot(index="channel", columns="yearmonth", values="광고비").fillna(0)
        fig_hm = px.imshow(hm_pivot, color_continuous_scale="Blues",
                           text_auto=".2s", title="월 × 채널 광고비", aspect="auto")
        fig_hm.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hm, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3: 채널 비교
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    ch = df.groupby("channel", observed=True).agg(
        광고비=("광고비","sum"), 광고노출=("광고노출","sum"), 광고클릭=("광고클릭","sum"),
        앱설치=("앱설치","sum"), 회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
        첫거래=("첫거래","sum"), 반복사용=("반복사용","sum"),
    ).reset_index()
    ch["CTR"]          = ch["광고클릭"] / ch["광고노출"]
    ch["설치율"]        = ch["앱설치"]  / ch["광고클릭"]
    ch["CPI"]          = ch["광고비"]   / ch["앱설치"]
    ch["CPA_회원가입"] = ch["광고비"]   / ch["회원가입"]
    ch["CPA_계좌개설"] = ch["광고비"]   / ch["계좌개설"]

    # ── 레이더 차트 ───────────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널별 성과 레이더 차트 (정규화)")
        radar_metrics = ["광고노출","광고클릭","앱설치","회원가입","계좌개설","첫거래"]
        ch_r = ch.set_index("channel")[radar_metrics].copy()
        ch_r_norm = (ch_r - ch_r.min()) / (ch_r.max() - ch_r.min() + 1e-9)
        fig_radar = go.Figure()
        for ch_name in ch_r_norm.index:
            vals = ch_r_norm.loc[ch_name].tolist() + [ch_r_norm.loc[ch_name].tolist()[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=radar_metrics + [radar_metrics[0]],
                fill="toself", name=ch_name,
                line_color=CHANNEL_COLOR.get(ch_name, "#888"),
            ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])),
                                paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── CTR / CPI 비교 ────────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널별 효율 비교")
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(ch, x="channel", y=["CTR","설치율"], barmode="group",
                         color_discrete_sequence=["#636EFA","#EF553B"],
                         title="CTR vs 설치전환율",
                         labels={"value":"비율","variable":"지표","channel":"채널"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig = px.bar(ch, x="channel", y=["CPI","CPA_회원가입","CPA_계좌개설"], barmode="group",
                         title="비용 효율 (CPI / CPA)",
                         labels={"value":"비용(₩)","variable":"지표","channel":"채널"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # ── 버블 차트 ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("광고비 vs 앱설치 버블 차트 (크기: 회원가입 수)")
        fig_bubble = px.scatter(ch, x="광고비", y="앱설치", size="회원가입",
                                color="channel", color_discrete_map=CHANNEL_COLOR,
                                text="channel", size_max=80,
                                labels={"광고비":"광고비(₩)","앱설치":"앱설치 수"})
        fig_bubble.update_traces(textposition="top center")
        fig_bubble.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bubble, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4: 캠페인·크리에이티브
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    obj_grp = df.groupby("campaign_objective", observed=True).agg(
        광고비=("광고비","sum"), 광고노출=("광고노출","sum"), 광고클릭=("광고클릭","sum"),
        앱설치=("앱설치","sum"), 회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
    ).reset_index()
    obj_grp["CTR"] = obj_grp["광고클릭"] / obj_grp["광고노출"]

    fmt_grp = df.groupby("creative_format", observed=True).agg(
        광고비=("광고비","sum"), 광고노출=("광고노출","sum"), 광고클릭=("광고클릭","sum"),
        앱설치=("앱설치","sum"), 회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
    ).reset_index()
    fmt_grp["CTR"] = fmt_grp["광고클릭"] / fmt_grp["광고노출"]
    fmt_grp["CPI"] = fmt_grp["광고비"]   / fmt_grp["앱설치"]

    # ── 캠페인 목적별 ─────────────────────────────────────────────────────────
    with st.container(border=True):
        card("캠페인 목적별 성과")
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(obj_grp, x="campaign_objective", y="광고비",
                         color="campaign_objective", title="광고비",
                         labels={"campaign_objective":"캠페인 목적","광고비":"광고비(₩)"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig = px.bar(obj_grp, x="campaign_objective", y="CTR",
                         color="campaign_objective", title="CTR",
                         labels={"campaign_objective":"캠페인 목적"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # ── 크리에이티브 포맷별 ───────────────────────────────────────────────────
    with st.container(border=True):
        card("크리에이티브 포맷별 성과")
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.bar(fmt_grp, x="creative_format", y="CTR",
                         color="creative_format", color_discrete_map=FORMAT_COLOR,
                         title="CTR (포맷별)", labels={"creative_format":"포맷"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            fig = px.bar(fmt_grp, x="creative_format", y="CPI",
                         color="creative_format", color_discrete_map=FORMAT_COLOR,
                         title="CPI — 낮을수록 효율적",
                         labels={"creative_format":"포맷","CPI":"CPI(₩)"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # ── 교차 히트맵 ───────────────────────────────────────────────────────────
    with st.container(border=True):
        card("채널 × 크리에이티브 포맷 교차 분석")
        cross_metric = st.selectbox("지표", ["광고비","앱설치","회원가입","계좌개설","CTR","CPI"], key="cross_metric")
        cross = df.groupby(["channel","creative_format"], observed=True).agg(
            광고비=("광고비","sum"), 광고클릭=("광고클릭","sum"), 광고노출=("광고노출","sum"),
            앱설치=("앱설치","sum"), 회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
        ).reset_index()
        cross["CTR"] = cross["광고클릭"] / cross["광고노출"]
        cross["CPI"] = cross["광고비"]   / cross["앱설치"]
        cp = cross.pivot(index="channel", columns="creative_format", values=cross_metric).fillna(0)
        fig_cp = px.imshow(cp, text_auto=".2s" if cross_metric not in ("CTR","CPI") else ".3f",
                           color_continuous_scale="Purp", aspect="auto")
        fig_cp.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cp, use_container_width=True)

    # ── 산점도 ────────────────────────────────────────────────────────────────
    with st.container(border=True):
        card("CTR vs CPI 산점도 (채널 × 포맷)")
        sc = df.groupby(["channel","creative_format","yearmonth"], observed=True).agg(
            광고비=("광고비","sum"), 광고클릭=("광고클릭","sum"),
            광고노출=("광고노출","sum"), 앱설치=("앱설치","sum"),
        ).reset_index()
        sc["CTR"] = sc["광고클릭"] / sc["광고노출"]
        sc["CPI"] = sc["광고비"]   / sc["앱설치"].replace(0, pd.NA)
        sc = sc.dropna(subset=["CPI"])
        fig_sc = px.scatter(sc, x="CTR", y="CPI", color="creative_format",
                            color_discrete_map=FORMAT_COLOR, facet_col="channel",
                            hover_data=["yearmonth","광고비","앱설치"], opacity=0.7,
                            labels={"CTR":"CTR","CPI":"CPI(₩)"})
        fig_sc.update_layout(height=430, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sc, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5: 퍼널 분석
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    # 퍼널을 노출(모수)과 클릭 이후로 분리
    FUNNEL_COLS_CLICK  = ["광고클릭","앱설치","앱실행","회원가입","계좌개설","첫거래","반복사용","자동이체설정","추천완료"]
    FUNNEL_LABELS_CLICK = ["클릭","앱설치","앱실행","회원가입","계좌개설","첫거래","반복사용","자동이체","추천완료"]
    FUNNEL_COLORS_CLICK = ["#2f4b7c","#665191","#a05195","#d45087","#f95d6a","#ff7c43","#ffa600","#66c2a5","#3288bd"]

    total_노출 = df["광고노출"].sum()
    total_클릭 = df["광고클릭"].sum()
    ctr_overall = total_클릭 / total_노출

    # ── 상단: 노출 모수 ───────────────────────────────────────────────────────
    with st.container(border=True):
        card("📡 노출 모수 (퍼널 진입 전)")
        col_노출, col_클릭, col_ctr, col_sp1, col_sp2 = st.columns(5)
        col_노출.metric("총 광고노출",  fmt_num(total_노출))
        col_클릭.metric("총 광고클릭",  fmt_num(total_클릭))
        col_ctr.metric("노출→클릭 CTR", fmt_pct(ctr_overall))
        col_sp1.empty()
        col_sp2.empty()

        st.markdown("<br>", unsafe_allow_html=True)

        # 채널별 노출 / CTR 나란히
        ch_imp = df.groupby("channel", observed=True).agg(
            광고노출=("광고노출","sum"),
            광고클릭=("광고클릭","sum"),
        ).reset_index()
        ch_imp["CTR"] = ch_imp["광고클릭"] / ch_imp["광고노출"]

        col_l, col_r = st.columns(2)
        with col_l:
            fig_imp = px.bar(
                ch_imp, x="channel", y="광고노출", color="channel",
                color_discrete_map=CHANNEL_COLOR,
                title="채널별 총 노출 수",
                labels={"channel":"채널", "광고노출":"노출 수"},
            )
            fig_imp.update_layout(showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_imp, use_container_width=True)
        with col_r:
            fig_ctr = px.bar(
                ch_imp, x="channel", y="CTR", color="channel",
                color_discrete_map=CHANNEL_COLOR,
                title="채널별 CTR (노출→클릭)",
                labels={"channel":"채널", "CTR":"CTR"},
            )
            fig_ctr.update_yaxes(tickformat=".2%")
            fig_ctr.update_layout(showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ctr, use_container_width=True)

    st.markdown(
        '<div style="text-align:center;color:#6B74C8;font-size:1.4rem;margin:4px 0;">▼ 클릭 이후 퍼널</div>',
        unsafe_allow_html=True,
    )

    # ── 전체 퍼널 (클릭부터) ─────────────────────────────────────────────────
    with st.container(border=True):
        card("전체 전환 퍼널 (클릭 → 추천완료)")
        funnel_vals = df[FUNNEL_COLS_CLICK].sum().tolist()
        fig_funnel = go.Figure(go.Funnel(
            y=FUNNEL_LABELS_CLICK, x=funnel_vals,
            textposition="inside", textinfo="value+percent initial",
            marker=dict(color=FUNNEL_COLORS_CLICK),
        ))
        fig_funnel.update_layout(height=460, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_funnel, use_container_width=True)

    # ── 채널별 퍼널 비교 (클릭부터) ──────────────────────────────────────────
    with st.container(border=True):
        card("채널별 퍼널 단계 비교 (클릭 이후)")
        funnel_ch = df.groupby("channel", observed=True)[FUNNEL_COLS_CLICK].sum().reset_index()
        fig_ch_f = go.Figure()
        for _, row in funnel_ch.iterrows():
            fig_ch_f.add_trace(go.Bar(
                name=row["channel"],
                x=FUNNEL_LABELS_CLICK,
                y=[row[c] for c in FUNNEL_COLS_CLICK],
                marker_color=CHANNEL_COLOR.get(row["channel"], "#888"),
            ))
        fig_ch_f.update_layout(
            barmode="group", xaxis_title="퍼널 단계", yaxis_title="수",
            height=430, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_ch_f, use_container_width=True)

    # ── 단계별 전환율 테이블 ──────────────────────────────────────────────────
    with st.container(border=True):
        card("단계별 전환율")
        all_cols   = ["광고노출"] + FUNNEL_COLS_CLICK
        all_labels = ["노출"]    + FUNNEL_LABELS_CLICK
        rows = []
        for (lf, cf), (lt, ct) in zip(
            zip(all_labels[:-1], all_cols[:-1]),
            zip(all_labels[1:],  all_cols[1:]),
        ):
            tf, tt = df[cf].sum(), df[ct].sum()
            is_top = (cf == "광고노출")
            rows.append({
                "단계": f"{lf} → {lt}",
                "이전 단계": f"{tf:,.0f}",
                "다음 단계": f"{tt:,.0f}",
                "전환율": fmt_pct(tt / tf if tf else 0),
                "비고": "노출 모수" if is_top else "",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── 월별 전환율 추이 ──────────────────────────────────────────────────────
    with st.container(border=True):
        card("월별 핵심 전환율 추이 (클릭 이후)")
        mf = df.groupby("yearmonth", observed=True).agg(
            광고클릭=("광고클릭","sum"), 앱설치=("앱설치","sum"),
            회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"), 첫거래=("첫거래","sum"),
        ).reset_index()
        mf["클릭→설치"]         = mf["앱설치"]   / mf["광고클릭"]
        mf["설치→회원가입"]     = mf["회원가입"] / mf["앱설치"]
        mf["회원가입→계좌개설"] = mf["계좌개설"] / mf["회원가입"]
        mf["계좌개설→첫거래"]   = mf["첫거래"]   / mf["계좌개설"]
        conv_cols = ["클릭→설치","설치→회원가입","회원가입→계좌개설","계좌개설→첫거래"]
        fig_cv = px.line(
            mf.melt(id_vars="yearmonth", value_vars=conv_cols, var_name="단계", value_name="전환율"),
            x="yearmonth", y="전환율", color="단계", markers=True,
            labels={"yearmonth":"월","전환율":"전환율"},
        )
        fig_cv.update_layout(
            yaxis_tickformat=".1%",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_cv, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 6: 통계 검정
# ════════════════════════════════════════════════════════════════════════════════
with tab6:
    from scipy import stats
    from itertools import combinations

    # ── 유틸: p값 해석 ────────────────────────────────────────────────────────
    def sig_label(p: float) -> str:
        if p < 0.001: return "✅ p < 0.001  (매우 유의)"
        if p < 0.01:  return "✅ p < 0.01   (유의)"
        if p < 0.05:  return "✅ p < 0.05   (유의)"
        return "❌ p ≥ 0.05  (유의하지 않음)"

    def result_box(title: str, stat_name: str, stat_val: float, p: float, h0: str, interp: str):
        """검정 결과를 카드로 출력"""
        sig = p < 0.05
        border_color = "#6B74C8" if sig else "#AAAAAA"
        bg = "#F0F2FF" if sig else "#F7F7F7"
        st.markdown(f"""
        <div style="border-left:4px solid {border_color};background:{bg};
                    border-radius:8px;padding:14px 18px;margin-bottom:12px;">
          <div style="font-size:1rem;font-weight:700;color:#2E3670;margin-bottom:6px;">{title}</div>
          <div style="font-size:0.82rem;color:#555;margin-bottom:8px;">H₀: {h0}</div>
          <div style="font-size:0.95rem;font-weight:600;">
            {stat_name} = {stat_val:.4f} &nbsp;|&nbsp; p = {p:.4f} &nbsp;|&nbsp; {sig_label(p)}
          </div>
          <div style="font-size:0.88rem;color:#3A449A;margin-top:8px;">💡 {interp}</div>
        </div>
        """, unsafe_allow_html=True)

    # 일별 집계 (검정용)
    daily = df.groupby(["date","channel","creative_format","campaign_objective"], observed=True).agg(
        광고비=("광고비","sum"), 광고노출=("광고노출","sum"), 광고클릭=("광고클릭","sum"),
        앱설치=("앱설치","sum"), 회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
    ).reset_index()
    daily["CTR"]  = daily["광고클릭"] / daily["광고노출"].replace(0, pd.NA)
    daily["CPI"]  = daily["광고비"]   / daily["앱설치"].replace(0, pd.NA)
    daily["설치전환율"]    = daily["앱설치"]   / daily["광고클릭"].replace(0, pd.NA)
    daily["회원가입전환율"] = daily["회원가입"] / daily["앱설치"].replace(0, pd.NA)

    # ════════════════════════════════════════════════════════════════════════
    # 1. 채널별 지표 차이 — One-way ANOVA + 사후 쌍별 t검정
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        card("① 채널 간 성과 차이 — One-way ANOVA")

        test_metric_map = {
            "CTR (클릭률)": "CTR",
            "CPI (설치당 비용)": "CPI",
            "설치전환율": "설치전환율",
            "회원가입전환율": "회원가입전환율",
        }
        sel_label = st.selectbox("검정할 지표 선택", list(test_metric_map.keys()), key="anova_metric")
        sel_col   = test_metric_map[sel_label]

        groups = [grp[sel_col].dropna().values for _, grp in daily.groupby("channel", observed=True)]
        ch_names = daily["channel"].unique().tolist()

        f_stat, p_anova = stats.f_oneway(*groups)
        interp_anova = (
            f"세 채널({', '.join(ch_names)})의 {sel_label}에 통계적으로 유의한 차이가 있습니다. 아래 사후검정으로 어느 채널이 다른지 확인하세요."
            if p_anova < 0.05 else
            f"세 채널의 {sel_label}에 통계적으로 유의한 차이가 없습니다. 채널 간 성과가 유사한 수준입니다."
        )
        result_box(
            f"One-way ANOVA — 채널별 {sel_label}",
            "F", f_stat, p_anova,
            f"세 채널의 {sel_label} 모집단 평균이 모두 같다",
            interp_anova,
        )

        # 박스플롯
        fig_box = px.box(
            daily.dropna(subset=[sel_col]),
            x="channel", y=sel_col, color="channel",
            color_discrete_map=CHANNEL_COLOR,
            points="outliers",
            title=f"채널별 {sel_label} 분포",
            labels={"channel":"채널", sel_col:sel_label},
        )
        fig_box.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

        # 쌍별 사후 검정 (Bonferroni 보정)
        st.markdown("**사후 검정 — 쌍별 독립표본 t-검정 (Bonferroni 보정)**")
        pairs = list(combinations(ch_names, 2))
        n_comp = len(pairs)
        rows_post = []
        for ch_a, ch_b in pairs:
            a = daily.loc[daily["channel"] == ch_a, sel_col].dropna()
            b = daily.loc[daily["channel"] == ch_b, sel_col].dropna()
            t_stat, p_raw = stats.ttest_ind(a, b, equal_var=False)
            p_adj = min(p_raw * n_comp, 1.0)  # Bonferroni
            rows_post.append({
                "비교": f"{ch_a} vs {ch_b}",
                f"평균({ch_a})": f"{a.mean():.4f}",
                f"평균({ch_b})": f"{b.mean():.4f}",
                "t 통계량": f"{t_stat:.3f}",
                "p (보정 전)": f"{p_raw:.4f}",
                "p (Bonferroni)": f"{p_adj:.4f}",
                "유의(α=0.05)": "✅" if p_adj < 0.05 else "❌",
            })
        st.dataframe(pd.DataFrame(rows_post), use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════════════════════
    # 2. 크리에이티브 포맷별 CPI 차이 — Kruskal-Wallis
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        card("② 크리에이티브 포맷별 CPI 차이 — Kruskal-Wallis 검정")
        st.caption("정규성 가정 없이 분포 차이를 검정하는 비모수 검정입니다.")

        fmt_names = daily["creative_format"].unique().tolist()
        fmt_groups = [daily.loc[daily["creative_format"] == f, "CPI"].dropna().values for f in fmt_names]
        h_stat, p_kw = stats.kruskal(*fmt_groups)
        interp_kw = (
            f"포맷({', '.join(fmt_names)}) 간 CPI에 유의한 차이가 있습니다. 특정 포맷이 더 효율적입니다."
            if p_kw < 0.05 else
            "포맷 간 CPI 차이가 통계적으로 유의하지 않습니다."
        )
        result_box(
            "Kruskal-Wallis — 포맷별 CPI",
            "H", h_stat, p_kw,
            "모든 크리에이티브 포맷의 CPI 분포가 동일하다",
            interp_kw,
        )

        fig_fmt = px.box(
            daily.dropna(subset=["CPI"]),
            x="creative_format", y="CPI", color="creative_format",
            color_discrete_map=FORMAT_COLOR,
            points="outliers",
            title="크리에이티브 포맷별 CPI 분포",
            labels={"creative_format":"포맷", "CPI":"CPI (₩)"},
        )
        fig_fmt.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              showlegend=False)
        st.plotly_chart(fig_fmt, use_container_width=True)

        # Mann-Whitney 사후 쌍별
        st.markdown("**사후 검정 — Mann-Whitney U 쌍별 비교 (Bonferroni 보정)**")
        fmt_pairs = list(combinations(fmt_names, 2))
        n_fp = len(fmt_pairs)
        rows_fmt = []
        for fa, fb in fmt_pairs:
            a = daily.loc[daily["creative_format"] == fa, "CPI"].dropna()
            b = daily.loc[daily["creative_format"] == fb, "CPI"].dropna()
            u_stat, p_raw = stats.mannwhitneyu(a, b, alternative="two-sided")
            p_adj = min(p_raw * n_fp, 1.0)
            rows_fmt.append({
                "비교": f"{fa} vs {fb}",
                f"중앙값({fa})": f"₩{a.median():,.0f}",
                f"중앙값({fb})": f"₩{b.median():,.0f}",
                "U 통계량": f"{u_stat:.0f}",
                "p (Bonferroni)": f"{p_adj:.4f}",
                "유의(α=0.05)": "✅" if p_adj < 0.05 else "❌",
            })
        st.dataframe(pd.DataFrame(rows_fmt), use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════════════════════
    # 3. 캠페인 목적별 CTR 차이 — 독립표본 t검정
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        card("③ 캠페인 목적별 CTR 차이 — 독립표본 t검정 (Welch's t-test)")

        obj_a, obj_b = "회원가입", "계좌개설"
        ctr_a = daily.loc[daily["campaign_objective"] == obj_a, "CTR"].dropna()
        ctr_b = daily.loc[daily["campaign_objective"] == obj_b, "CTR"].dropna()
        t_stat_obj, p_obj = stats.ttest_ind(ctr_a, ctr_b, equal_var=False)

        col_l, col_r = st.columns(2)
        col_l.metric(f"평균 CTR — {obj_a} 캠페인", fmt_pct(ctr_a.mean()))
        col_r.metric(f"평균 CTR — {obj_b} 캠페인", fmt_pct(ctr_b.mean()))

        result_box(
            "Welch's t-test — 캠페인 목적별 CTR",
            "t", t_stat_obj, p_obj,
            f"'{obj_a}' 캠페인과 '{obj_b}' 캠페인의 CTR 평균이 같다",
            (f"두 캠페인 목적 간 CTR에 유의한 차이가 있습니다. "
             f"{'회원가입' if ctr_a.mean() > ctr_b.mean() else '계좌개설'} 캠페인의 CTR이 더 높습니다."
             if p_obj < 0.05 else
             "두 캠페인 목적 간 CTR 차이가 통계적으로 유의하지 않습니다."),
        )

        fig_obj = px.histogram(
            daily.dropna(subset=["CTR"]),
            x="CTR", color="campaign_objective", barmode="overlay",
            opacity=0.65, nbins=60,
            title="캠페인 목적별 CTR 분포",
            labels={"CTR":"CTR","campaign_objective":"캠페인 목적"},
        )
        fig_obj.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_obj, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # 4. 월별 광고비 트렌드 — Mann-Kendall 단조 트렌드 검정
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        card("④ 월별 트렌드 유의성 — Mann-Kendall 검정")
        st.caption("시계열 데이터에 단조적인 증가/감소 트렌드가 있는지 검정합니다.")

        trend_options = {"광고비":"광고비","앱설치":"앱설치","회원가입":"회원가입",
                         "계좌개설":"계좌개설","CTR":"CTR"}
        sel_trend_label = st.selectbox("트렌드 검정 지표", list(trend_options.keys()), key="mk_metric")
        sel_trend_col   = trend_options[sel_trend_label]

        monthly_trend = df.groupby("yearmonth", observed=True).agg(
            광고비=("광고비","sum"), 앱설치=("앱설치","sum"),
            회원가입=("회원가입","sum"), 계좌개설=("계좌개설","sum"),
            광고클릭=("광고클릭","sum"), 광고노출=("광고노출","sum"),
        ).reset_index().sort_values("yearmonth")
        monthly_trend["CTR"] = monthly_trend["광고클릭"] / monthly_trend["광고노출"]
        series = monthly_trend[sel_trend_col].dropna().values

        # Mann-Kendall: scipy.stats.kendalltau(x, rank(x))로 근사
        n_pts = len(series)
        x_rank = pd.Series(range(n_pts))
        tau, p_mk = stats.kendalltau(x_rank, series)

        direction = "증가" if tau > 0 else "감소"
        interp_mk = (
            f"월별 {sel_trend_label}에 통계적으로 유의한 {direction} 트렌드가 있습니다. (τ={tau:.3f})"
            if p_mk < 0.05 else
            f"월별 {sel_trend_label}에서 유의한 단조 트렌드가 발견되지 않았습니다. 계절성이나 외부 요인을 추가로 확인해보세요."
        )
        result_box(
            f"Mann-Kendall 트렌드 검정 — 월별 {sel_trend_label}",
            "τ (Kendall's tau)", tau, p_mk,
            f"월별 {sel_trend_label}에 단조 트렌드가 없다 (무작위 변동)",
            interp_mk,
        )

        # 트렌드 라인 포함 시각화
        import numpy as np
        x_vals = np.arange(n_pts)
        slope, intercept = np.polyfit(x_vals, series, 1)
        trend_line = slope * x_vals + intercept

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=monthly_trend["yearmonth"], y=series,
            mode="lines+markers", name=sel_trend_label,
            line=dict(color="#6B74C8", width=2), marker=dict(size=7),
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly_trend["yearmonth"], y=trend_line,
            mode="lines", name="추세선 (OLS)",
            line=dict(color="#EF553B", width=2, dash="dash"),
        ))
        fig_trend.update_layout(
            title=f"월별 {sel_trend_label} + 추세선",
            xaxis_title="월", yaxis_title=sel_trend_label,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # 5. 채널 × 포맷 전환율 — 카이제곱 독립성 검정
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        card("⑤ 채널 × 크리에이티브 포맷 독립성 — 카이제곱 검정")
        st.caption("채널 선택과 크리에이티브 포맷이 서로 독립인지 (조합이 균등한지) 검정합니다.")

        ct = pd.crosstab(df["channel"], df["creative_format"])
        chi2, p_chi, dof, expected = stats.chi2_contingency(ct)

        result_box(
            "카이제곱 독립성 검정 — 채널 × 크리에이티브 포맷",
            "χ²", chi2, p_chi,
            "채널과 크리에이티브 포맷 선택이 서로 독립이다",
            (f"채널과 크리에이티브 포맷 간에 유의한 연관성이 있습니다. (dof={dof}) "
             "특정 채널에서 특정 포맷이 집중적으로 사용되는 패턴이 있습니다."
             if p_chi < 0.05 else
             "채널과 크리에이티브 포맷 선택 간에 유의한 연관성이 없습니다."),
        )

        # 관찰 빈도 히트맵
        fig_chi = px.imshow(
            ct, text_auto=True, color_continuous_scale="Blues",
            title="채널 × 포맷 관찰 빈도 (행 수)",
            aspect="auto",
        )
        fig_chi.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_chi, use_container_width=True)

        # 표준화 잔차 (어떤 셀이 기대보다 높은가)
        st.markdown("**표준화 잔차** — 양수(파랑)는 기대보다 많음, 음수(빨강)는 기대보다 적음")
        obs = ct.values.astype(float)
        std_resid = (obs - expected) / (expected ** 0.5)
        std_resid_df = pd.DataFrame(std_resid, index=ct.index, columns=ct.columns)
        fig_resid = px.imshow(
            std_resid_df, text_auto=".2f",
            color_continuous_scale="RdBu", color_continuous_midpoint=0,
            title="표준화 잔차 히트맵", aspect="auto",
        )
        fig_resid.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_resid, use_container_width=True)
