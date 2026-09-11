# 신대방 맛집 챗봇 — 논리 ERD

물리 스키마(SQL DDL) 23개 테이블 기준으로 작성. 카디널리티 표기는 아래 범례를 따른다.

**범례**: `||` 정확히 1, `|o` 0 또는 1(선택), `o{` 0개 이상, `}|` 1개 이상

---

## 1. 서비스 도메인 (11개 테이블)

사용자·대화·추천·평가 흐름의 핵심 엔티티.

```mermaid
erDiagram
    PROFILES ||--o{ CONVERSATIONS : "작성"
    CONVERSATIONS ||--o{ MESSAGES : "포함"
    RESTAURANT_CATEGORIES |o--o{ RESTAURANTS : "분류(선택)"
    RESTAURANTS ||--o{ MENUS : "보유"
    TAG_CATEGORIES ||--o{ RESTAURANT_TAGS : "분류"
    RESTAURANTS ||--o{ RESTAURANT_TAG_MAP : "매핑"
    RESTAURANT_TAGS ||--o{ RESTAURANT_TAG_MAP : "매핑"
    PROFILES ||--o{ USER_CONSENTS : "동의"
    PROFILES ||--o{ RECOMMENDATIONS : "요청"
    CONVERSATIONS ||--o{ RECOMMENDATIONS : "발생"
    RESTAURANTS ||--o{ RECOMMENDATIONS : "추천됨"
    PROFILES ||--o{ FEEDBACK : "남김"
    CONVERSATIONS ||--o{ FEEDBACK : "관련"
    RESTAURANTS ||--o{ FEEDBACK : "대상"
    RECOMMENDATIONS ||--o{ FEEDBACK : "평가"

    PROFILES {
        uuid id PK
        varchar profile_nickname
        char profile_status
        char profile_type
    }
    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        varchar title
    }
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        varchar role
        text content
    }
    RESTAURANT_CATEGORIES {
        uuid id PK
        varchar name
    }
    RESTAURANTS {
        uuid id PK
        uuid category_id FK
        varchar name
        varchar address
        boolean is_active
    }
    MENUS {
        uuid id PK
        uuid restaurant_id FK
        varchar name
        integer price
    }
    TAG_CATEGORIES {
        uuid id PK
        varchar code
        varchar name
    }
    RESTAURANT_TAGS {
        uuid id PK
        uuid category_id FK
        varchar name
    }
    RESTAURANT_TAG_MAP {
        uuid restaurant_id PK_FK
        uuid tag_id PK_FK
    }
    USER_CONSENTS {
        uuid id PK
        uuid profile_id FK
        varchar consent_type
        boolean is_agreed
    }
    RECOMMENDATIONS {
        uuid id PK
        uuid profile_id FK
        uuid conversation_id FK
        uuid restaurant_id FK
        jsonb conditions
        varchar reason_source
    }
    FEEDBACK {
        uuid feedback_id PK
        uuid profile_id FK
        uuid conversation_id FK
        uuid restaurant_id FK
        uuid recommendation_id FK
        char feedback_value
    }
```

![1_서비스도메인 ERD](./ERD_이미지/1_서비스도메인.png)


**비고**: `RESTAURANT_TAG_MAP`은 RESTAURANTS–RESTAURANT_TAGS 간 N:M 관계를 해소하는 연결 엔티티(복합 PK). `feedback_value`는 1=불만족/2=보통/3=만족으로 확정됨.

---

## 2. 대시보드 도메인 (2개 테이블)

다른 테이블에서 배치 집계된 결과만 담는 독립 테이블 — 외부 FK 없음.

```mermaid
erDiagram
    DASHBOARD_SEARCH_STATS {
        uuid stat_id PK
        date stat_date
        char stat_type "0=카테고리/1=가격대/2=상황태그"
        varchar stat_key
        integer count
    }
    DASHBOARD_DATA_QUALITY {
        uuid stat_id PK
        integer total_restaurant
        integer complete_count "menus+tag 모두 보유"
        integer incomplete_count
    }
```

![2_대시보드도메인 ERD](./ERD_이미지/2_대시보드도메인.png)


**비고**: `dashboard_search_stats`는 `restaurants`, `menus`, `restaurant_tag_map` 등에서 집계 배치로 채워지나, FK 관계가 아닌 파생 데이터이므로 관계선 없음(원천 테이블은 위 서비스 도메인 참조).

---

## 3. 로그분석 파이프라인 도메인 (9개 테이블 + PROFILES 참조)

M1(로그수집)~M7(개선실험) 대응 구간.

```mermaid
erDiagram
    PROFILES |o--o{ API_REQUEST_LOGS : "발생(선택)"
    LOG_CLEANING_RUNS ||--o{ LOG_CLEANING_RESULTS : "포함"
    API_REQUEST_LOGS ||--o{ LOG_CLEANING_RESULTS : "정제됨"
    LOG_CLEANING_RUNS ||--o{ API_STATISTICS : "집계"
    PROFILES ||--o{ LOG_SUMMARIES : "요청"
    LOG_CLEANING_RUNS ||--o{ LOG_SUMMARIES : "기반"
    LOG_SUMMARIES ||--o{ LOG_SUMMARY_EVIDENCE : "근거제시"
    API_REQUEST_LOGS ||--o{ LOG_SUMMARY_EVIDENCE : "근거로사용"
    SUMMARY_EVALUATION_CASES ||--o{ SUMMARY_EVALUATION_RUNS : "평가"
    LOG_SUMMARIES ||--o{ SUMMARY_EVALUATION_RUNS : "평가대상"
    IMPROVEMENT_EXPERIMENTS |o--o{ SUMMARY_EVALUATION_RUNS : "실험연계(선택)"

    PROFILES {
        uuid id PK
    }
    API_REQUEST_LOGS {
        uuid id PK
        uuid profile_id FK
        varchar http_method
        varchar endpoint_path
        smallint status_code
        integer response_time_ms
    }
    LOG_CLEANING_RUNS {
        uuid id PK
        timestamptz period_start
        timestamptz period_end
        varchar status
    }
    LOG_CLEANING_RESULTS {
        uuid cleaning_run_id PK_FK
        uuid api_log_id PK_FK
        boolean is_included
    }
    API_STATISTICS {
        uuid id PK
        uuid cleaning_run_id FK
        varchar endpoint
        integer request_count
        integer error_count
    }
    LOG_SUMMARIES {
        uuid id PK
        uuid requested_by FK
        uuid cleaning_run_id FK
        text summary_text
        varchar status
    }
    LOG_SUMMARY_EVIDENCE {
        uuid summary_id PK_FK
        uuid api_log_id PK_FK
        smallint evidence_order
    }
    SUMMARY_EVALUATION_CASES {
        uuid id PK
        varchar name
        jsonb expected_facts
    }
    IMPROVEMENT_EXPERIMENTS {
        uuid id PK
        varchar name
        varchar status
    }
    SUMMARY_EVALUATION_RUNS {
        uuid id PK
        uuid case_id FK
        uuid summary_id FK
        uuid experiment_id FK
        varchar run_type
        numeric total_score
    }
```

![3_로그분석파이프라인도메인 ERD](./ERD_이미지/3_로그분석파이프라인도메인.png)


**비고**: `LOG_CLEANING_RESULTS`, `LOG_SUMMARY_EVIDENCE`는 각각 (정제실행×원본로그), (요약×원본로그) N:M 연결 엔티티. `PROFILES`는 서비스 도메인 엔티티를 여기서는 참조용으로만 축약 표기.

---

## 남은 3NF 방어 논리 메모

`RECOMMENDATIONS.conditions`, `LOG_SUMMARIES.filters`, `SUMMARY_EVALUATION_CASES.expected_facts`는 JSONB 컬럼이다. 조건/필터 구조가 가변적이라 실무적으로 비정규화 채택 — 최종 정의서에 "의도적 비정규화, 사유: 가변 조건 구조" 명시 필요.
