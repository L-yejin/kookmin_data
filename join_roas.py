"""채널 × AppsFlyer 조인 → ROAS 계산
raw/channel/*.csv + raw/appsflyer/*.csv 를 DuckDB로 읽어 조인 후
  output/joined_roas.parquet  (내부용)
  output/joined_roas.csv      (공유용, UTF-8 BOM — 엑셀 한글 정상 표시)
로 저장.

파일이 늘어나도 glob 패턴으로 자동 처리됨.
"""
from pathlib import Path
import duckdb

BASE   = Path(__file__).resolve().parent
CH_PAT = str(BASE / "raw/channel/*.csv")
AF_PAT = str(BASE / "raw/appsflyer/*.csv")
OUT_DIR = BASE / "output"
OUT_PARQUET = OUT_DIR / "joined_roas.parquet"
OUT_CSV     = OUT_DIR / "joined_roas.csv"

OUT_DIR.mkdir(exist_ok=True)

con = duckdb.connect()

con.execute("""
    CREATE TABLE ch AS
    SELECT * FROM read_csv_auto(?, union_by_name=true)
""", [CH_PAT])

con.execute("""
    CREATE TABLE af AS
    SELECT *,
        CASE 미디어소스
            WHEN 'googleadwords_int' THEN '구글'
            WHEN 'Facebook Ads'      THEN '메타'
            WHEN 'naver_search'      THEN '네이버'
        END AS 채널
    FROM read_csv_auto(?, union_by_name=true)
""", [AF_PAT])

con.execute("""
    CREATE TABLE result AS
    SELECT
        ch.일,
        ch.채널,
        ch.채널분류,
        ch.캠페인,
        ch.캠페인목적,
        ch.그룹,
        ch.소재,
        ch.노출,
        ch.클릭    AS 클릭_ch,
        af.클릭    AS 클릭_af,
        ch.비용,
        ch.회원가입  AS 회원가입_ch,
        af.회원가입  AS 회원가입_af,
        ch.구매    AS 구매_ch,
        af.구매    AS 구매_af,
        ch.구매매출  AS 구매매출_ch,
        af.구매매출  AS 구매매출_af,
        ROUND(af.구매매출 / NULLIF(ch.비용, 0), 2) AS ROAS
    FROM ch
    LEFT JOIN af
        ON  ch.일     = af.일
        AND ch.채널   = af.채널
        AND ch.캠페인  = af.캠페인
        AND ch.그룹    = af.그룹
        AND ch.소재    = af.소재
    ORDER BY ch.일, ch.채널, ch.캠페인, ch.그룹, ch.소재
""")

# ── 내부용: Parquet ────────────────────────────────────────────────────────────
con.execute(f"COPY result TO '{OUT_PARQUET}' (FORMAT PARQUET)")

# ── 공유용: CSV (UTF-8 BOM) — DuckDB로 쓴 뒤 BOM 앞에 삽입 ──────────────────
_tmp = OUT_DIR / "_tmp.csv"
con.execute(f"COPY result TO '{_tmp}' (HEADER, DELIMITER ',')")
with open(_tmp, "rb") as f:
    content = f.read()
with open(OUT_CSV, "wb") as f:
    f.write(b"\xef\xbb\xbf" + content)   # UTF-8 BOM
_tmp.unlink()

# ── 요약 출력 ──────────────────────────────────────────────────────────────────
row_count = con.execute("SELECT COUNT(*) FROM result").fetchone()[0]
date_count, d_min, d_max = con.execute(
    "SELECT COUNT(DISTINCT 일), MIN(일), MAX(일) FROM result"
).fetchone()
summary = con.execute("""
    SELECT
        채널,
        SUM(비용)       AS 총비용,
        SUM(구매매출_af) AS 총매출_af,
        ROUND(SUM(구매매출_af) / NULLIF(SUM(비용), 0), 2) AS ROAS
    FROM result
    GROUP BY 채널
    ORDER BY ROAS DESC
""").df()

print(f"기간: {d_min} ~ {d_max}  ({date_count}일치, {row_count:,}행)")
print(f"  내부용 → {OUT_PARQUET.name}  ({OUT_PARQUET.stat().st_size:,} bytes)")
print(f"  공유용 → {OUT_CSV.name}      ({OUT_CSV.stat().st_size:,} bytes)")
print()
print("=== 채널별 ROAS ===")
print(summary.to_string(index=False))
