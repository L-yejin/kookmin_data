# 채널 매핑 규칙

채널 데이터의 `채널` 컬럼과 AppsFlyer의 `미디어소스` 컬럼을 조인할 때 사용하는 매핑표.

## 매핑 테이블

| 채널명 (내부) | AF 미디어소스 | 약어 | 컬러 | 분류 |
|---|---|---|---|---|
| 구글 | `googleadwords_int` | GGL | `#4285F4` | 외부 |
| 메타 | `Facebook Ads` | META | `#1877F2` | 외부 |
| 네이버 | `naver_search` | NVR | `#03C75A` | 자체 |
| 카카오 *(예정)* | `kakao_moment` | KKO | `#FEE500` | 외부 |
| 틱톡 *(예정)* | `TikTok_Ads` | TTK | `#000000` | 외부 |

## 사용 규칙

- 조인 시 AF `미디어소스` → 내부 `채널명`으로 **변환 후** 키로 사용한다.
- `채널분류` 가 `자체`(네이버)인 경우 외부 채널과 ROAS를 직접 비교하지 않는다. 예산 성격이 다르기 때문.
- 신규 채널 추가 시 이 문서에 먼저 등록 후 코드에 반영한다.

## DuckDB 구현 예시

```sql
CASE 미디어소스
    WHEN 'googleadwords_int' THEN '구글'
    WHEN 'Facebook Ads'      THEN '메타'
    WHEN 'naver_search'      THEN '네이버'
    WHEN 'kakao_moment'      THEN '카카오'
    WHEN 'TikTok_Ads'        THEN '틱톡'
END AS 채널
```

## TODO

- [ ] 카카오·틱톡 실제 집행 시작 시 컬러·약어 확정
