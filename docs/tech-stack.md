# 기술 스택 및 코딩 규칙

## 환경

| 항목 | 설정 |
|---|---|
| Python | `~/anaconda3/bin/python` (3.11.4) 고정 |
| 패키지 관리 | Anaconda (pip install 시 `~/anaconda3/bin/pip` 사용) |

## 라이브러리 사용 원칙

| 라이브러리 | 용도 | 규칙 |
|---|---|---|
| **DuckDB** | 데이터 로딩·조인·집계 | 기본. pandas 대신 사용 |
| **pandas** | 요약 출력·소형 연산 | DuckDB 결과를 `.df()` 로 변환할 때만 |
| **Streamlit** | 대시보드 |  |
| **Plotly** | 차트 |  |

## 파일 포맷 규칙

| 상황 | 포맷 | 이유 |
|---|---|---|
| 내부 저장 | **Parquet** | 빠른 읽기, 컬럼형 압축 |
| 외부 공유 | **CSV (UTF-8 BOM)** | 엑셀 한글 깨짐 방지 |

CSV 저장 방법 (BOM 삽입):
```python
# DuckDB로 임시 CSV 저장 후 BOM 앞에 삽입
con.execute(f"COPY result TO '{tmp}' (HEADER, DELIMITER ',')")
with open(tmp, "rb") as f:
    content = f.read()
with open(out_csv, "wb") as f:
    f.write(b"\xef\xbb\xbf" + content)
tmp.unlink()
```

## DuckDB 패턴

```python
# 날짜별 파일 전체 읽기 (glob)
read_csv_auto('raw/channel/*.csv', union_by_name=true)

# 0 나누기 방지
ROUND(af.구매매출 / NULLIF(ch.비용, 0), 2)

# 결과 저장: 항상 Parquet + CSV 세트
con.execute(f"COPY result TO '{out}.parquet' (FORMAT PARQUET)")
```

## 대시보드 규칙

- 차트 배경: `paper_bgcolor="rgba(0,0,0,0)"` (테마 연동)
- 테마 설정: `.streamlit/config.toml` 에서 관리
- 실행: `~/anaconda3/bin/streamlit run fintech_dashboard.py`
