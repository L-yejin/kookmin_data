"""퍼포먼스 마케팅 종합 대시보드
채널 × AppsFlyer 기반 6탭 분석
"""
from pathlib import Path
import warnings; warnings.filterwarnings("ignore")

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="퍼마 대시보드", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.stApp{background:#EFF1FB}
[data-testid="stSidebar"]{background:#E2E6F5;border-right:1px solid #C9CEEA}
.sc{background:#FFF;border:1px solid #D4D8F0;border-radius:14px;
    padding:20px 24px;margin-bottom:18px;box-shadow:0 2px 10px rgba(107,116,200,.07)}
.st{font-size:1rem;font-weight:700;color:#2E3670;margin-bottom:12px;
    padding-bottom:8px;border-bottom:2px solid #E2E6F5}
[data-testid="stMetric"]{background:#FFF;border:1px solid #D4D8F0;border-radius:12px;
    padding:14px 18px;box-shadow:0 2px 8px rgba(107,116,200,.1)}
[data-testid="stMetricLabel"]{color:#5058A0!important;font-size:.82rem!important;font-weight:700!important}
[data-testid="stMetricValue"]{color:#1E2340!important;font-size:1.35rem!important;font-weight:800!important}
[data-testid="stTabs"] [role="tab"]{font-size:.92rem;font-weight:600;color:#5058A0;padding:8px 12px}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{color:#6B74C8;border-bottom:3px solid #6B74C8}
h1,h2,h3{color:#2E3670!important}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE   = Path(__file__).resolve().parent
CH_PAT = str(BASE / "raw/channel/*.csv")
AF_PAT = str(BASE / "raw/appsflyer/*.csv")

CH_COLOR   = {"구글":"#4285F4","메타":"#1877F2","네이버":"#03C75A"}
TYPE_COLOR = {"VID":"#6B74C8","IMG":"#EF553B","CRS":"#00CC96","TXT":"#FFA500"}
ROAS_GOOD, ROAS_BAD = 4.0, 2.0
RETARGET_OBJ = {"리타겟팅","재구매"}

# ── Data load ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_raw(ch_pat: str, af_pat: str) -> pd.DataFrame:
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
    df = con.execute("""
        SELECT
            ch.일::DATE        AS 일,
            ch.채널, ch.채널분류, ch.캠페인, ch.캠페인목적, ch.그룹, ch.소재,
            ch.노출,
            ch.클릭            AS 클릭_ch,
            ch.비용,
            ch.회원가입        AS 회원가입_ch,
            ch.구매            AS 구매_ch,
            ch.구매매출        AS 구매매출_ch,
            COALESCE(af.클릭,    0) AS 클릭_af,
            COALESCE(af.회원가입,0) AS 회원가입_af,
            COALESCE(af.구매,    0) AS 구매_af,
            COALESCE(af.구매매출,0) AS 구매매출_af
        FROM ch
        LEFT JOIN af
            ON  ch.일=af.일 AND ch.채널=af.채널
            AND ch.캠페인=af.캠페인 AND ch.그룹=af.그룹 AND ch.소재=af.소재
    """).df()
    df["일"] = pd.to_datetime(df["일"])
    return df

def parse_creatives(df: pd.DataFrame) -> pd.DataFrame:
    def _p(name):
        pts = str(name).split("_")
        if len(pts) >= 5: return pts[0], pts[1], pts[2], pts[3], pts[4], True
        if len(pts) == 4: return pts[0], pts[1], pts[2], None,    pts[3], False
        return pts[0], "-", "-", None, "-", False
    cols = ["cr_타입","cr_카테고리","cr_시즌","cr_AB","cr_버전","cr_AB여부"]
    return pd.concat([df, df["소재"].apply(_p).apply(pd.Series).set_axis(cols, axis=1)], axis=1)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_num(v, pre="", suf=""):
    if pd.isna(v): return "-"
    if abs(v) >= 1e8: return f"{pre}{v/1e8:.1f}억{suf}"
    if abs(v) >= 1e4: return f"{pre}{v/1e4:.0f}만{suf}"
    return f"{pre}{v:,.0f}{suf}"

def fmt_pct(v): return f"{v*100:.2f}%" if not pd.isna(v) else "-"
def sig(v):     return "⚫" if pd.isna(v) else "🟢" if v>=ROAS_GOOD else "🟡" if v>=ROAS_BAD else "🔴"

def roas_bar(roas, mx=20):
    if pd.isna(roas): return ""
    pct = min(roas/mx*100, 100)
    c = "#2ECC71" if roas>=ROAS_GOOD else "#F39C12" if roas>=ROAS_BAD else "#E74C3C"
    return (f'<div style="display:flex;align-items:center;gap:6px">'
            f'<div style="flex:1;background:#E2E6F5;border-radius:4px;height:10px">'
            f'<div style="background:{c};width:{pct:.0f}%;height:10px;border-radius:4px"></div></div>'
            f'<span style="font-size:.85rem;font-weight:700;color:#1E2340;min-width:36px">{roas:.2f}</span>'
            f'</div>')

def card(t): st.markdown(f'<div class="st">{t}</div>', unsafe_allow_html=True)

def clayout(fig, h=380):
    fig.update_layout(height=h, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=36,b=16,l=0,r=0))
    return fig

def kpi_agg(df, 매출c, 가입c, 구매c):
    """전체 집계 + WoW 계산"""
    dates = sorted(df["일"].unique())
    r7 = set(dates[-7:]);  p7 = set(dates[-14:-7])
    def wow(col):
        c = df[df["일"].isin(r7)][col].sum()
        p = df[df["일"].isin(p7)][col].sum() if p7 else None
        d = f"{(c-p)/p*100:+.1f}%" if (p and p>0) else None
        return c, d
    비용_v, d_비용 = wow("비용")
    매출_v, d_매출 = wow(매출c)
    가입_v, d_가입 = wow(가입c)
    노출_v  = df["노출"].sum()
    클릭_v  = df["클릭_ch"].sum()
    구매_v  = df[구매c].sum()
    구매ch_v= df["구매_ch"].sum()
    return dict(
        비용=비용_v, d_비용=d_비용,
        노출=노출_v,
        ctr=클릭_v/노출_v if 노출_v else None,
        가입=가입_v, d_가입=d_가입,
        cac=비용_v/가입_v if 가입_v else None,
        roas=round(매출_v/비용_v,2) if 비용_v else None, d_매출=d_매출,
        cover=구매_v/구매ch_v if 구매ch_v else None,
    )

def gagg(df, by, 매출c, 가입c, 구매c):
    g = df.groupby(by, observed=True).agg(
        광고비=("비용","sum"), 노출=("노출","sum"), 클릭_ch=("클릭_ch","sum"),
        매출=(매출c,"sum"), 가입=(가입c,"sum"), 구매=(구매c,"sum"),
        구매_ch=("구매_ch","sum"),
    ).reset_index()
    g["ROAS"]   = (g["매출"]/g["광고비"].replace(0,pd.NA)).round(2)
    g["CTR"]    = (g["클릭_ch"]/g["노출"].replace(0,pd.NA)*100).round(3)
    g["CAC"]    = (g["광고비"]/g["가입"].replace(0,pd.NA)).round(0)
    g["AF커버"] = (g["구매"]/g["구매_ch"].replace(0,pd.NA)*100).round(1)
    return g

# ── Load ──────────────────────────────────────────────────────────────────────
raw = parse_creatives(load_raw(CH_PAT, AF_PAT))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 필터")

    d_min, d_max = raw["일"].min().date(), raw["일"].max().date()
    dr = st.date_input("기간", value=(d_min, d_max), min_value=d_min, max_value=d_max)

    st.markdown("---")
    sel_cls = st.multiselect("채널분류", sorted(raw["채널분류"].unique()),
                              default=sorted(raw["채널분류"].unique()))
    sel_ch  = st.multiselect("채널",     sorted(raw["채널"].unique()),
                              default=sorted(raw["채널"].unique()))
    sel_obj = st.multiselect("캠페인 목적", sorted(raw["캠페인목적"].unique()),
                              default=sorted(raw["캠페인목적"].unique()))
    sel_grp = st.multiselect("타겟 그룹",  sorted(raw["그룹"].unique()),
                              default=sorted(raw["그룹"].unique()))

    st.markdown("---")
    st.markdown("**소재 속성**")
    sel_typ = st.multiselect("타입",    sorted(raw["cr_타입"].unique()),
                              default=sorted(raw["cr_타입"].unique()))
    sel_cat = st.multiselect("카테고리", sorted(raw["cr_카테고리"].unique()),
                              default=sorted(raw["cr_카테고리"].unique()))
    sel_sea = st.multiselect("시즌",    sorted(raw["cr_시즌"].unique()),
                              default=sorted(raw["cr_시즌"].unique()))

    st.markdown("---")
    excl_brand = st.toggle("브랜드KW 제외", value=True,
                            help="캠페인목적='브랜드KW' 행 제외 (CLAUDE.md §6-1)")
    use_af     = st.toggle("AF 기준 지표", value=True,
                            help="OFF 시 채널 자체 보고 수치 사용")

# ── Apply filters ─────────────────────────────────────────────────────────────
s = pd.Timestamp(dr[0]) if len(dr)==2 else pd.Timestamp(d_min)
e = pd.Timestamp(dr[1]) if len(dr)==2 else pd.Timestamp(d_max)

df = raw[
    (raw["일"] >= s) & (raw["일"] <= e) &
    raw["채널분류"].isin(sel_cls) & raw["채널"].isin(sel_ch) &
    raw["캠페인목적"].isin(sel_obj) & raw["그룹"].isin(sel_grp) &
    raw["cr_타입"].isin(sel_typ) & raw["cr_카테고리"].isin(sel_cat) &
    raw["cr_시즌"].isin(sel_sea)
].copy()

if excl_brand:
    df = df[df["캠페인목적"] != "브랜드KW"]

if df.empty:
    st.warning("선택 조건에 해당하는 데이터가 없습니다."); st.stop()

sfx  = "af" if use_af else "ch"
매출c = f"구매매출_{sfx}"
가입c = f"회원가입_{sfx}"
구매c = f"구매_{sfx}"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📊 퍼포먼스 마케팅 종합 대시보드")
st.markdown(
    f'<div style="font-size:.85rem;color:#5058A0;margin-bottom:14px">'
    f'기간: <b>{s.date()} ~ {e.date()}</b> &nbsp;|&nbsp; '
    f'지표 기준: <b>{"AppsFlyer" if use_af else "채널 보고"}</b>'
    f'{"  |  브랜드KW 제외" if excl_brand else ""}'
    f'</div>', unsafe_allow_html=True
)

# ── KPI Row ───────────────────────────────────────────────────────────────────
with st.container(border=True):
    kpi = kpi_agg(df, 매출c, 가입c, 구매c)
    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric("총 광고비",    fmt_num(kpi["비용"],"₩"),  delta=kpi["d_비용"])
    c2.metric("총 노출",      fmt_num(kpi["노출"]))
    c3.metric("CTR",          fmt_pct(kpi["ctr"]) if kpi["ctr"] else "-")
    c4.metric("신규 가입",    fmt_num(kpi["가입"]),        delta=kpi["d_가입"])
    c5.metric("CAC",          fmt_num(kpi["cac"],"₩")    if kpi["cac"] else "-")
    c6.metric(f'ROAS {sig(kpi["roas"])}',
              f'{kpi["roas"]:.2f}' if kpi["roas"] else "-", delta=kpi["d_매출"])
    c7.metric("AF 커버리지",  fmt_pct(kpi["cover"])       if kpi["cover"] else "-")

st.caption("WoW: 최근 7일 vs 직전 7일 비교")

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5,t6 = st.tabs([
    "📈 전체 추세","🎯 목적별","🎨 소재 속성",
    "🅰️🅱️ A/B 테스트","👥 타겟그룹","🏆 캠페인 랭킹",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1: 전체 추세
# ════════════════════════════════════════════════════════════════════════════
with t1:
    daily = df.groupby("일").agg(
        광고비=("비용","sum"), 매출=(매출c,"sum"),
        클릭_ch=("클릭_ch","sum"), 노출=("노출","sum"),
    ).reset_index()
    daily["ROAS"] = (daily["매출"]/daily["광고비"].replace(0,pd.NA)).round(2)

    daily_ch = df.groupby(["일","채널"]).agg(
        광고비=("비용","sum"), 매출=(매출c,"sum"),
    ).reset_index()
    daily_ch["ROAS"] = (daily_ch["매출"]/daily_ch["광고비"].replace(0,pd.NA)).round(2)

    with st.container(border=True):
        card("📈 일별 광고비 vs 매출 (이중축)")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily["일"], y=daily["광고비"],
                             name="광고비", marker_color="#6B74C8", opacity=0.7))
        fig.add_trace(go.Scatter(x=daily["일"], y=daily["매출"], name="매출",
                                 line=dict(color="#EF553B",width=2.5),
                                 yaxis="y2", mode="lines+markers", marker_size=4))
        fig.update_layout(
            yaxis=dict(title="광고비 (₩)", showgrid=False),
            yaxis2=dict(title="매출 (₩)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1), hovermode="x unified",
        )
        clayout(fig, 400); st.plotly_chart(fig, use_container_width=True)

    with st.container(border=True):
        card("📡 채널별 ROAS 추이")
        fig2 = px.line(daily_ch, x="일", y="ROAS", color="채널",
                       color_discrete_map=CH_COLOR, markers=True,
                       labels={"일":"","채널":"채널"})
        fig2.add_hline(y=ROAS_GOOD, line_dash="dot", line_color="#2E3670",
                       annotation_text="기준 4.0")
        fig2.add_hline(y=ROAS_BAD, line_dash="dot", line_color="#EF553B",
                       annotation_text="위험 2.0")
        clayout(fig2, 360); st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2: 목적별
# ════════════════════════════════════════════════════════════════════════════
with t2:
    obj = gagg(df, "캠페인목적", 매출c, 가입c, 구매c).sort_values("ROAS", ascending=False)
    obj["분류"] = obj["캠페인목적"].apply(
        lambda x: "🔄 리타겟팅/재구매" if x in RETARGET_OBJ else "🆕 신규")

    with st.container(border=True):
        card("🎯 캠페인 목적별 ROAS  (신규 vs 리타겟팅 분리)")
        fig = px.bar(obj, x="캠페인목적", y="ROAS", color="분류",
                     color_discrete_map={"🆕 신규":"#6B74C8","🔄 리타겟팅/재구매":"#FFA500"},
                     labels={"캠페인목적":"","ROAS":"ROAS"})
        fig.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670",
                      annotation_text="기준 4.0")
        clayout(fig); st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            card("광고비 비중")
            fig2 = px.pie(obj, names="캠페인목적", values="광고비", hole=0.4)
            clayout(fig2, 320); st.plotly_chart(fig2, use_container_width=True)
    with col_r:
        with st.container(border=True):
            card("매출 비중")
            fig3 = px.pie(obj, names="캠페인목적", values="매출", hole=0.4)
            clayout(fig3, 320); st.plotly_chart(fig3, use_container_width=True)

    with st.container(border=True):
        card("목적별 KPI 테이블")
        d = obj.copy()
        d["광고비"] = d["광고비"].apply(lambda x: fmt_num(x,"₩"))
        d["매출"]   = d["매출"].apply(lambda x: fmt_num(x,"₩"))
        d["ROAS"]   = d.apply(lambda r: f"{sig(r['ROAS'])} {r['ROAS']}" if not pd.isna(r['ROAS']) else "-", axis=1)
        d["CTR"]    = d["CTR"].apply(lambda x: f"{x:.2f}%" if not pd.isna(x) else "-")
        d["CAC"]    = d["CAC"].apply(lambda x: fmt_num(x,"₩") if not pd.isna(x) else "-")
        d["AF커버"] = d["AF커버"].apply(lambda x: f"{x:.1f}%" if not pd.isna(x) else "-")
        st.dataframe(d[["캠페인목적","분류","광고비","매출","ROAS","CTR","가입","CAC","AF커버"]],
                     use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3: 소재 속성
# ════════════════════════════════════════════════════════════════════════════
with t3:
    def cagg(by): return gagg(df, by, 매출c, 가입c, 구매c)

    with st.container(border=True):
        card("🎨 소재 타입별 성과")
        tp = cagg("cr_타입").sort_values("ROAS", ascending=False)
        cl, cr_ = st.columns(2)
        with cl:
            f = px.bar(tp, x="cr_타입", y="ROAS", color="cr_타입",
                       color_discrete_map=TYPE_COLOR, labels={"cr_타입":""})
            f.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670")
            clayout(f, 300); st.plotly_chart(f, use_container_width=True)
        with cr_:
            f2 = px.bar(tp, x="cr_타입", y="CTR", color="cr_타입",
                        color_discrete_map=TYPE_COLOR, labels={"cr_타입":""})
            clayout(f2, 300); st.plotly_chart(f2, use_container_width=True)

    with st.container(border=True):
        card("📦 카테고리별 ROAS")
        cat = cagg("cr_카테고리").sort_values("ROAS", ascending=False)
        f3 = px.bar(cat, x="cr_카테고리", y="ROAS", color="ROAS",
                    color_continuous_scale="Blues", labels={"cr_카테고리":""})
        f3.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670")
        clayout(f3, 300); st.plotly_chart(f3, use_container_width=True)

    with st.container(border=True):
        card("🌸 시즌별 ROAS")
        sea = cagg("cr_시즌").sort_values("ROAS", ascending=False)
        f4 = px.bar(sea, x="cr_시즌", y="ROAS", color="ROAS",
                    color_continuous_scale="Purp", labels={"cr_시즌":""})
        f4.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670")
        clayout(f4, 280); st.plotly_chart(f4, use_container_width=True)

    with st.container(border=True):
        card("🗺️ 타입 × 카테고리 ROAS 히트맵")
        hm_df = (
            df.groupby(["cr_타입","cr_카테고리"], observed=True)
            .apply(lambda x: round(x[매출c].sum()/x["비용"].sum(), 2) if x["비용"].sum()>0 else None)
            .reset_index(name="ROAS")
        )
        hm = hm_df.pivot(index="cr_타입", columns="cr_카테고리", values="ROAS")
        f5 = px.imshow(hm, text_auto=".2f", color_continuous_scale="Blues",
                       aspect="auto", labels={"x":"카테고리","y":"타입"})
        f5.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(f5, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4: A/B 테스트
# ════════════════════════════════════════════════════════════════════════════
with t4:
    ab = df[df["cr_AB여부"]].copy()

    if ab.empty:
        st.info("현재 필터 조건에 A/B 소재가 없습니다.")
    else:
        # 페어 키: 채널/목적/카테고리/시즌/타입/버전
        ab["pair"] = (ab["채널"] + "|" + ab["캠페인목적"] + "|" +
                      ab["cr_카테고리"] + "|" + ab["cr_시즌"] + "|" +
                      ab["cr_타입"] + "|" + ab["cr_버전"])
        ab["pair_label"] = (ab["채널"] + " · " + ab["cr_카테고리"] +
                            " · " + ab["cr_타입"] + " · " + ab["cr_버전"])

        ab_grp = ab.groupby(["pair","pair_label","cr_AB"], observed=True).agg(
            광고비=("비용","sum"), 매출=(매출c,"sum"),
            클릭_ch=("클릭_ch","sum"), 노출=("노출","sum"), 가입=(가입c,"sum"),
        ).reset_index()
        ab_grp["ROAS"] = (ab_grp["매출"]/ab_grp["광고비"].replace(0,pd.NA)).round(2)
        ab_grp["CTR"]  = (ab_grp["클릭_ch"]/ab_grp["노출"].replace(0,pd.NA)*100).round(3)

        ab_wide = ab_grp.pivot_table(
            index=["pair","pair_label"], columns="cr_AB",
            values=["ROAS","CTR","광고비"], aggfunc="mean"
        ).round(3).reset_index()
        ab_wide.columns = [f"{a}_{b}" if b else a for a,b in ab_wide.columns]

        if "ROAS_A" in ab_wide.columns and "ROAS_B" in ab_wide.columns:
            ab_wide["승자"] = ab_wide.apply(
                lambda r: "🅰️ A" if (pd.notna(r.get("ROAS_A")) and pd.notna(r.get("ROAS_B"))
                                    and r["ROAS_A"] > r["ROAS_B"])
                else ("🅱️ B" if pd.notna(r.get("ROAS_B")) else "-"), axis=1
            )
            ab_wide["ΔROAS(B-A)"] = (ab_wide.get("ROAS_B",pd.NA) -
                                      ab_wide.get("ROAS_A",pd.NA)).round(2)

        with st.container(border=True):
            card("🧪 A/B 페어 요약 테이블")
            show_cols = [c for c in ["pair_label","ROAS_A","ROAS_B","ΔROAS(B-A)","승자",
                                      "CTR_A","CTR_B","광고비_A","광고비_B"] if c in ab_wide.columns]
            st.dataframe(ab_wide[show_cols].rename(columns={"pair_label":"소재(공통)"}),
                         use_container_width=True, hide_index=True)

        with st.container(border=True):
            card("📊 A vs B ROAS 비교")
            ab_plot = ab_grp[ab_grp["cr_AB"].isin(["A","B"])].copy()
            fig = px.bar(ab_plot, x="pair_label", y="ROAS", color="cr_AB",
                         barmode="group",
                         color_discrete_map={"A":"#6B74C8","B":"#EF553B"},
                         labels={"pair_label":"","cr_AB":"A/B"})
            fig.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670",
                          annotation_text="기준 4.0")
            fig.update_xaxes(tickangle=30)
            clayout(fig, 420); st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 5: 타겟그룹
# ════════════════════════════════════════════════════════════════════════════
with t5:
    grp = gagg(df, "그룹", 매출c, 가입c, 구매c).sort_values("ROAS", ascending=False)

    with st.container(border=True):
        card("👥 타겟 그룹별 ROAS")
        fig = px.bar(grp, x="그룹", y="ROAS", color="ROAS",
                     color_continuous_scale="Blues", labels={"그룹":""})
        fig.add_hline(y=ROAS_GOOD, line_dash="dash", line_color="#2E3670",
                      annotation_text="기준 4.0")
        clayout(fig, 320); st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            card("광고비 비중")
            fig2 = px.pie(grp, names="그룹", values="광고비", hole=0.4)
            clayout(fig2, 300); st.plotly_chart(fig2, use_container_width=True)
    with col_r:
        with st.container(border=True):
            card("그룹 × 채널 ROAS 히트맵")
            cross = (
                df.groupby(["그룹","채널"], observed=True)
                .apply(lambda x: round(x[매출c].sum()/x["비용"].sum(),2) if x["비용"].sum()>0 else None)
                .reset_index(name="ROAS")
            )
            hm2 = cross.pivot(index="그룹", columns="채널", values="ROAS")
            fig3 = px.imshow(hm2, text_auto=".2f", color_continuous_scale="Blues", aspect="auto")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig3, use_container_width=True)

    with st.container(border=True):
        card("그룹별 KPI 테이블")
        d = grp.copy()
        d["광고비"] = d["광고비"].apply(lambda x: fmt_num(x,"₩"))
        d["매출"]   = d["매출"].apply(lambda x: fmt_num(x,"₩"))
        d["ROAS"]   = d.apply(lambda r: f"{sig(r['ROAS'])} {r['ROAS']}" if not pd.isna(r['ROAS']) else "-", axis=1)
        d["CTR"]    = d["CTR"].apply(lambda x: f"{x:.2f}%" if not pd.isna(x) else "-")
        d["CAC"]    = d["CAC"].apply(lambda x: fmt_num(x,"₩") if not pd.isna(x) else "-")
        d["AF커버"] = d["AF커버"].apply(lambda x: f"{x:.1f}%" if not pd.isna(x) else "-")
        st.dataframe(d[["그룹","광고비","매출","ROAS","CTR","가입","CAC","AF커버"]],
                     use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 6: 캠페인 랭킹
# ════════════════════════════════════════════════════════════════════════════
with t6:
    cmp = gagg(df, "캠페인", 매출c, 가입c, 구매c)
    obj_map = df.groupby("캠페인", observed=True)["캠페인목적"].first()
    cmp["캠페인목적"] = cmp["캠페인"].map(obj_map)
    cmp["분류"] = cmp["캠페인목적"].apply(
        lambda x: "🔄 리타겟팅" if x in RETARGET_OBJ else "🆕 신규")
    cmp["신호"] = cmp["ROAS"].apply(sig)

    seg = st.radio("", ["전체","🆕 신규","🔄 리타겟팅"], horizontal=True, label_visibility="collapsed")
    cmp_f = cmp if seg=="전체" else cmp[cmp["분류"]==seg]
    cmp_f = cmp_f.sort_values("ROAS", ascending=False)

    top_n = st.slider("표시 캠페인 수", 5, min(50,len(cmp_f)), min(20,len(cmp_f)))
    show  = cmp_f.head(top_n).reset_index(drop=True)

    with st.container(border=True):
        card(f"🏆 캠페인 ROAS 랭킹 — {seg}  ({len(cmp_f)}개 중 상위 {top_n}개)")

        rows = ""
        for _, r in show.iterrows():
            rows += (
                f"<tr style='border-bottom:1px solid #F0F2FF'>"
                f"<td style='padding:7px 10px;font-size:1.1rem'>{r['신호']}</td>"
                f"<td style='padding:7px 10px;font-size:.83rem;color:#2E3670'>{r['캠페인']}</td>"
                f"<td style='padding:7px 10px;text-align:center;font-size:.82rem'>{r.get('캠페인목적','-')}</td>"
                f"<td style='padding:7px 10px;min-width:180px'>{roas_bar(r['ROAS'])}</td>"
                f"<td style='padding:7px 10px;text-align:right;font-size:.83rem'>{fmt_num(r['광고비'],'₩')}</td>"
                f"<td style='padding:7px 10px;text-align:right;font-size:.83rem'>{fmt_num(r['매출'],'₩')}</td>"
                f"<td style='padding:7px 10px;text-align:right;font-size:.83rem'>{r['CTR']:.2f}%</td>"
                f"</tr>"
            )
        st.markdown(f"""
        <table style='width:100%;border-collapse:collapse;font-family:sans-serif'>
          <thead>
            <tr style='background:#E2E6F5;font-size:.78rem;color:#2E3670'>
              <th style='padding:8px 10px;text-align:left'>상태</th>
              <th style='padding:8px 10px;text-align:left'>캠페인</th>
              <th style='padding:8px 10px;text-align:center'>목적</th>
              <th style='padding:8px 10px;text-align:left'>ROAS</th>
              <th style='padding:8px 10px;text-align:right'>광고비</th>
              <th style='padding:8px 10px;text-align:right'>매출</th>
              <th style='padding:8px 10px;text-align:right'>CTR</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)
