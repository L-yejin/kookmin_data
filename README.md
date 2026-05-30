# 퍼포먼스 마케팅 데이터 대시보드

채널 광고 데이터와 AppsFlyer 기여 데이터를 일별로 조인·전처리하여  
채널 / 소재 / 캠페인별 인사이트를 시각화하는 Streamlit 대시보드 프로젝트.

---

## 라이브 데모

> 배포 완료 후 URL을 여기에 추가 예정

---

## 주요 기능

### 📊 pma_dashboard.py — 퍼포먼스 마케팅 종합 대시보드

| 탭 | 내용 |
|---|---|
| 📈 전체 추세 | 일별 광고비 vs 매출 이중축 차트 + 채널별 ROAS 추이 |
| 🎯 목적별 | 캠페인 목적별 ROAS (신규 vs 리타겟팅 분리) · 비용/매출 비중 |
| 🎨 소재 속성 | 타입·카테고리·시즌별 성과 + 타입×카테고리 히트맵 |
| 🅰️🅱️ A/B 테스트 | 같은 조건 내 A·B 소재 자동 페어링 · 승자 표시 |
| 👥 타겟그룹 | 논타겟·유사타겟·리마케팅·VIP·윈백 성과 비교 |
| 🏆 캠페인 랭킹 | 🟢🟡🔴 신호등 + ROAS 프로그레스바 |

**상단 KPI Row** — 총 광고비 / 노출 / CTR / 신규가입 / CAC / ROAS / AF 커버리지  
각 지표에 **WoW delta** (최근 7일 vs 직전 7일) 자동 표시

**사이드바 필터** — 기간 / 채널분류 / 채널 / 캠페인 목적 / 타겟 그룹 / 소재 속성 (타입·카테고리·시즌) / 브랜드KW 제외 토글 / AF↔채널 지표 기준 전환

---

## 데이터 구조

```
raw/
├── channel/          # 채널별 광고 집행 데이터 (일별 CSV)
│   └── YYYY-MM-DD.csv
└── appsflyer/        # AppsFlyer 기여(Attribution) 데이터 (일별 CSV)
    └── YYYY-MM-DD.csv
```

### channel CSV 컬럼
`일` · `채널` · `채널분류` · `캠페인` · `캠페인목적` · `그룹` · `소재` · `노출` · `클릭` · `비용` · `회원가입` · `구매` · `구매매출`

### appsflyer CSV 컬럼
`일` · `미디어소스` · `캠페인` · `그룹` · `소재` · `클릭` · `회원가입` · `구매` · `구매매출`

### 조인 키
`일 / 채널 / 캠페인 / 그룹 / 소재`

### KPI 계산 기준
| KPI | 계산식 |
|---|---|
| CTR | 클릭(ch) / 노출(ch) |
| ROAS | 구매매출(AF) / 비용(ch) |
| CAC | 비용(ch) / 회원가입(AF) |
| AF 커버리지 | 구매(AF) / 구매(ch) |

---

## 채널 매핑

| 채널 (내부) | AF 미디어소스 | 약어 | 컬러 |
|---|---|---|---|
| 구글 | `googleadwords_int` | GGL | `#4285F4` |
| 메타 | `Facebook Ads` | META | `#1877F2` |
| 네이버 | `naver_search` | NVR | `#03C75A` |

---

## 소재 네이밍 규칙

```
{타입}_{카테고리}_{시즌}_{AB}_{버전}   ← AB 있을 때 (5파트)
{타입}_{카테고리}_{시즌}_{버전}        ← AB 없을 때 (4파트)

예) VID_플러스멤버십_겨울_A_v2
    IMG_적립혜택_상시_v1
```

| 타입 | 의미 |
|---|---|
| VID | 영상 |
| IMG | 이미지 |
| CRS | 카루셀 |
| TXT | 텍스트 |

---

## 파일 구조

```
kookmin_data/
├── pma_dashboard.py          # 메인 대시보드 (6탭)
├── channel_dashboard.py      # 채널 일별 스냅샷 + 소재 리더보드
├── fintech_dashboard.py      # 핀테크 EDA 대시보드 (통계 검정 포함)
├── join_roas.py              # 채널 × AF 조인 → Parquet/CSV 저장
├── requirements.txt
├── CLAUDE.md                 # 프로젝트 규칙 목차
├── raw/
│   ├── channel/              # 일별 채널 광고 원본 (읽기 전용)
│   ├── appsflyer/            # 일별 AF 기여 원본 (읽기 전용)
│   └── braze/                # Braze CRM 데이터
├── docs/
│   ├── channel-mapping.md    # 채널명 ↔ AF 미디어소스 매핑
│   ├── creative-naming.md    # 소재 네이밍 규칙 + 파싱 코드
│   ├── campaign-structure.md # 캠페인 목적 · 타겟 그룹 정의
│   ├── kpi-definitions.md    # KPI 계산식 · 기준선
│   ├── data-sources.md       # Truth Source 원칙 · 이상치 기준
│   └── tech-stack.md         # Python 환경 · DuckDB 패턴
└── .streamlit/
    └── config.toml           # 연한 푸른연보라 테마
```

---

## 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 메인 대시보드 실행
streamlit run pma_dashboard.py

# 3. 채널 조인 + ROAS 계산 (output/ 저장)
python join_roas.py
```

> **Python 환경**: `~/anaconda3/bin/python` (3.11.4) 권장

---

## 기술 스택

| 항목 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| 데이터 처리 | DuckDB (대용량), pandas (소형 연산) |
| 시각화 | Plotly, Streamlit |
| 저장 포맷 | Parquet (내부) · CSV UTF-8 BOM (공유) |
| 통계 검정 | scipy (ANOVA, t-test, Kruskal-Wallis, Mann-Kendall) |

---

## 데이터 기간

현재 레포지토리에 포함된 데이터: **2025-01-01 ~ 2025-03-31 (90일, 가상 데이터)**

새 날짜 데이터 추가 방법:
```
raw/channel/YYYY-MM-DD.csv    추가
raw/appsflyer/YYYY-MM-DD.csv  추가
python join_roas.py            실행
```
glob 패턴으로 자동 인식되어 전체 기간이 반영됩니다.
