# 퍼포먼스 마케팅 데이터 파이프라인

매일 채널 광고 데이터와 AppsFlyer 기여 데이터를 조인·전처리하여
채널/소재/캠페인별 인사이트를 생산하는 프로젝트.

---

## 규칙 문서 목록

| 문서 | 내용 |
|---|---|
| [채널 매핑](docs/channel-mapping.md) | 내부 채널명 ↔ AF 미디어소스 매핑, 컬러·약어 |
| [소재 네이밍](docs/creative-naming.md) | 소재명 구조, 타입·카테고리·시즌·AB 정의, 파싱 코드 |
| [캠페인 구조](docs/campaign-structure.md) | 캠페인 목적, 타겟 그룹, 분석 시 주의사항 |
| [KPI 정의](docs/kpi-definitions.md) | CTR·CPI·CPA·ROAS 계산식, 기준선, 0 처리 규칙 |
| [데이터 소스](docs/data-sources.md) | channel vs AF 역할 구분, Truth Source 원칙, 이상치 감지 |
| [기술 스택](docs/tech-stack.md) | Python 환경, DuckDB 패턴, 파일 포맷 규칙 |

---

## 빠른 참조

- **조인 키**: 일 / 채널 / 캠페인 / 그룹 / 소재
- **ROAS**: `AF 구매매출 / 채널 비용` (분모 0이면 NULL)
- **저장 포맷**: 내부 → Parquet, 공유 → CSV (UTF-8 BOM)
- **Python 실행**: `~/anaconda3/bin/python`
- **raw/ 파일**: 읽기 전용, 절대 수정 금지

---

## 미확정 항목 (TODO)

- [ ] Attribution window (클릭 후 며칠 이내 전환 인정)
- [ ] View-through attribution 사용 여부
- [ ] ROAS 양호/위험 기준선 (임시: 4.0 / 2.0)
- [ ] 소재 타입 BNR 사용 여부
- [ ] 시즌 코드 전체 목록 (봄·여름·가을)
- [ ] 카카오·틱톡 캠페인 네이밍 규칙
- [ ] 외부 공유 파일 비용·매출 단위 처리
