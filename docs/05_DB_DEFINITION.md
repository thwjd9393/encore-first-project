# 신대방 맛집 챗봇 — 물리 ERD (테이블 정의서)

논리 ERD와 동일한 3개 도메인 구조로 작성. SQL DDL 기준 전체 23개 테이블.
표기: **PK**=기본키, **FK**=외래키, **U**=UNIQUE

---

## 1. 서비스 도메인 (11개 테이블)

### profiles
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | - | PK | FK→auth.users(id) ON DELETE CASCADE | 사용자 고유 ID (Supabase Auth 연동) |
| profile_login_id | varchar(45) | Y | - | U | - | 로그인 아이디 |
| profile_nickname | varchar(45) | N | - | U | - | 사용자 닉네임 |
| kakao_profile_id | varchar(100) | Y | - | U | - | 카카오 프로필 ID |
| profile_created_at | timestamptz | N | current_timestamp | - | - | 프로필 생성일시 |
| profile_updated_at | timestamptz | Y | - | - | - | 프로필 수정일시 |
| profile_withdrawn_at | timestamptz | Y | - | - | - | 회원 탈퇴일시 |
| profile_status | char(1) | N | '1' | - | CHECK IN ('0','1') | 0=탈퇴, 1=가입 |
| profile_type | char(1) | N | '1' | - | CHECK IN ('0','1') | 0=관리자, 1=일반 사용자 |

### conversations
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 대화방 고유 ID |
| user_id | uuid | N | - | FK | →profiles(id) ON DELETE CASCADE | 대화방 소유 사용자 |
| title | varchar(100) | Y | - | - | - | 대화방 제목 |
| created_at | timestamptz | N | now() | - | - | 생성일시 |
| updated_at | timestamptz | N | now() | - | - | 수정일시 |
| deleted_at | timestamptz | Y | - | - | - | 소프트 삭제 일시 |

### messages
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 메시지 고유 ID |
| conversation_id | uuid | N | - | FK | →conversations(id) ON DELETE CASCADE | 소속 대화방 |
| role | varchar(20) | N | - | - | CHECK IN ('user','assistant','system') | 작성 역할 |
| content | text | N | - | - | - | 메시지 내용 |
| created_at | timestamptz | N | now() | - | - | 생성일시 |

### restaurant_categories
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 카테고리 고유 ID |
| name | varchar(30) | N | - | U | - | 한식/중식/일식/양식/기타 |

### restaurants
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 음식점 고유 ID |
| category_id | uuid | Y | - | FK | →restaurant_categories(id) ON DELETE SET NULL | 음식 카테고리(선택) |
| name | varchar(100) | N | - | - | - | 음식점 이름 |
| address | varchar(255) | Y | - | - | - | 주소 |
| phone | varchar(30) | Y | - | - | - | 전화번호 |
| description | varchar(500) | Y | - | - | - | 설명 |
| storage_path | varchar(500) | Y | - | - | - | 이미지 저장 경로 (사진 파이프라인 미확정 — 확정 전까지 NULL 허용) |
| kakao_place_id | varchar(30) | Y | - | U(부분) | UNIQUE WHERE NOT NULL | 카카오 장소 ID |
| kakao_category_name | varchar(255) | Y | - | - | - | 카카오 분류명 |
| lot_address | varchar(255) | Y | - | - | - | 지번 주소 |
| road_address | varchar(255) | Y | - | - | - | 도로명 주소 |
| longitude | numeric(10,7) | Y | - | - | CHECK -180~180 | 경도 |
| latitude | numeric(10,7) | Y | - | - | CHECK -90~90 | 위도 |
| kakao_place_url | varchar(500) | Y | - | - | - | 카카오맵 URL |
| business_hours | text | Y | - | - | - | 영업시간 |
| break_time | text | Y | - | - | - | 브레이크타임 |
| source_url | varchar(500) | Y | - | - | - | 원천 출처 URL |
| last_verified_at | date | Y | - | - | - | 최종 확인일 |
| is_active | boolean | N | true | - | - | 노출 여부 |
| created_at | timestamptz | N | now() | - | - | 생성일시 |
| updated_at | timestamptz | N | now() | - | - | 수정일시 |

**참고**: 가격대(price_tier)는 물리 컬럼으로 두지 않고 `menus.price` 평균값에서 `dashboard_search_stats`로 배치 파생 — 팀 결정 반영, 원천값 중복저장 없음.

### menus
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 메뉴 고유 ID |
| restaurant_id | uuid | N | - | FK | →restaurants(id) ON DELETE CASCADE | 소속 음식점 |
| name | varchar(100) | N | - | - | - | 메뉴명 |
| price | integer | N | - | - | CHECK >=0 | 가격 |
| source_url | varchar(500) | Y | - | - | - | 출처 URL |
| last_verified_at | date | Y | - | - | - | 최종 확인일 |
| created_at | timestamptz | N | now() | - | - | 생성일시 |
| updated_at | timestamptz | N | current_timestamp | - | - | 수정일시 |
| (복합) | - | - | - | U | UNIQUE(restaurant_id, name) | 동일 식당 내 메뉴명 중복 방지 |

### tag_categories
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 태그 카테고리 ID |
| code | varchar(30) | N | - | U | - | 태그 카테고리 코드 |
| name | varchar(30) | N | - | U | - | 가격대/분위기/이용목적/맛 등 |

### restaurant_tags
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 태그 고유 ID |
| category_id | uuid | N | - | FK | →tag_categories(id) ON DELETE CASCADE | 소속 카테고리 |
| name | varchar(50) | N | - | U(복합: category_id+name) | - | 태그명 |

### restaurant_tag_map (연결 엔티티)
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| restaurant_id | uuid | N | - | PK,FK | →restaurants(id) ON DELETE CASCADE | 음식점 |
| tag_id | uuid | N | - | PK,FK | →restaurant_tags(id) ON DELETE CASCADE | 태그 |

### user_consents
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 동의 고유 ID |
| profile_id | uuid | N | - | FK | →profiles(id) | 동의 주체 |
| consent_type | varchar(30) | N | - | - | CHECK IN ('terms','privacy') | 약관 유형 |
| consent_version | varchar(30) | N | - | - | - | 약관 버전 |
| is_agreed | boolean | N | - | - | - | 동의 여부 |
| agreed_at | timestamptz | N | current_timestamp | - | - | 동의 시각 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |
| (복합) | - | - | - | U | UNIQUE(profile_id, consent_type, consent_version) | 중복 동의 방지 |

### recommendations
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 추천 결과 ID |
| request_id | uuid | N | - | U | - | 요청 고유 식별자 |
| profile_id | uuid | N | - | FK | →profiles(id) | 요청 사용자 |
| conversation_id | uuid | N | - | FK | →conversations(id) ON DELETE CASCADE | 발생 대화방 |
| restaurant_id | uuid | N | - | FK | →restaurants(id) | 추천된 음식점 |
| conditions | jsonb | N | '{}'::jsonb | - | CHECK jsonb_typeof=object | 추천 요청 조건 (의도적 비정규화) |
| reason_text | varchar(300) | Y | - | - | - | 추천 사유 텍스트 |
| reason_source | varchar(20) | N | 'gemini' | - | CHECK IN ('gemini','db_fallback') | 사유 생성 출처 |
| model_name | varchar(100) | Y | - | - | - | 사용 모델명 |
| prompt_version | varchar(50) | Y | - | - | - | 프롬프트 버전 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

### feedback
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| feedback_id | uuid | N | gen_random_uuid() | PK | - | 피드백 고유 ID |
| profile_id | uuid | N | - | FK | →profiles(id) ON DELETE CASCADE | 작성 사용자 |
| conversation_id | uuid | N | - | FK | →conversations(id) ON DELETE CASCADE | 관련 대화방 |
| restaurant_id | uuid | N | - | FK | →restaurants(id) ON DELETE CASCADE | 대상 음식점 |
| recommendation_id | uuid | N | - | FK | →recommendations(id) ON DELETE CASCADE | 평가 대상 추천 |
| feedback_value | char(1) | N | - | - | CHECK IN ('1','2','3') | **1=불만족, 2=보통, 3=만족** (확정) |
| created_at | timestamptz | N | current_timestamp | - | - | 작성 시각 |
| updated_at | timestamptz | Y | - | - | - | 변경 시각 |

**서비스 도메인 인덱스**: `uq_restaurants_kakao_place_id`(부분 UNIQUE), `uq_feedback_profile_recommendation`(UNIQUE), `uq_menus_restaurant_name`(UNIQUE), `idx_conversations_user_id`, `idx_messages_conversation_id`, `idx_messages_conversation_created_at`, `idx_restaurants_category_id`, `idx_restaurants_is_active`, `idx_menus_restaurant_id`, `idx_restaurant_tags_category_id`, `idx_restaurant_tag_map_restaurant_id`, `idx_restaurant_tag_map_tag_id`, `idx_feedback_profile_id`, `idx_feedback_conversation_id`, `idx_feedback_restaurant_id`, `idx_feedback_recommendation_id`, `idx_feedback_created_at`, `idx_feedback_profile_created_at`, `idx_recommendations_conversation_created_at`, `idx_recommendations_profile_created_at`

---

## 2. 대시보드 도메인 (2개 테이블)

### dashboard_search_stats
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| stat_id | uuid | N | gen_random_uuid() | PK | - | 검색 통계 고유 ID |
| stat_date | date | N | - | - | - | 집계 기준일 |
| stat_type | char(1) | N | - | - | CHECK IN ('0','1','2') | 0=음식카테고리, 1=가격대, 2=상황태그 |
| stat_key | varchar(45) | N | - | - | - | 항목값 (예: 한식/중/매운거) |
| count | integer | N | 0 | - | CHECK >=0 | 발생 건수 |
| created_at | timestamptz | N | current_timestamp | - | - | 배치 집계 시각 |
| (복합) | - | - | - | U | UNIQUE(stat_date, stat_type, stat_key) | 중복 집계 방지 |

### dashboard_data_quality
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| stat_id | uuid | N | gen_random_uuid() | PK | - | 품질 점검 고유 ID |
| checked_at | timestamptz | N | current_timestamp | - | - | 점검 시각 |
| total_restaurant | integer | N | 0 | - | CHECK >=0 | 전체 식당 수 |
| complete_count | integer | N | 0 | - | CHECK >=0 | **메뉴 1건 이상 + 태그 1건 이상 보유 식당 수** (확정) |
| incomplete_count | integer | N | 0 | - | CHECK >=0 | 정보 미완성 식당 수 |
| (테이블) | - | - | - | - | CHECK complete_count+incomplete_count=total_restaurant | 정합성 제약 |

**대시보드 도메인 인덱스**: `idx_dashboard_search_stats_date`, `idx_dashboard_search_stats_type`, `idx_dashboard_search_stats_date_type`

**참고**: FK 없음 — restaurants/menus/restaurant_tag_map에서 배치 집계로 파생, 논리 ERD의 "관계 없음" 표기와 일치.

---

## 3. 로그분석 파이프라인 도메인 (9개 테이블 + profiles 참조)

### api_request_logs
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 로그 고유 ID |
| request_id | uuid | N | - | U | - | 요청 고유 식별자 |
| profile_id | uuid | Y | - | FK | →profiles(id) ON DELETE SET NULL | 발생 사용자(선택, 비로그인 허용) |
| occurred_at | timestamptz | N | current_timestamp | - | - | 발생 시각 |
| http_method | varchar(10) | N | - | - | CHECK IN ('GET','POST','PATCH','DELETE') | HTTP 메서드 |
| endpoint_path | varchar(255) | N | - | - | - | 엔드포인트 경로 |
| status_code | smallint | N | - | - | CHECK 100~599 | 응답 상태코드 |
| response_time_ms | integer | N | - | - | CHECK >=0 | 응답 시간(ms) |
| error_code | varchar(50) | Y | - | - | - | 에러 코드 |
| client_type | varchar(30) | Y | - | - | - | 클라이언트 유형 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

### log_cleaning_runs
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 정제 실행 ID |
| period_start | timestamptz | N | - | - | CHECK start<end | 집계 시작 |
| period_end | timestamptz | N | - | - | - | 집계 종료 |
| criteria_version | varchar(50) | N | - | - | - | 정제 기준 버전 |
| status | varchar(20) | N | 'running' | - | CHECK IN ('running','succeeded','failed') | 실행 상태 |
| source_count | integer | N | 0 | - | CHECK >=0 | 원본 건수 |
| included_count | integer | N | 0 | - | CHECK >=0 | 포함 건수 |
| excluded_count | integer | N | 0 | - | CHECK >=0 | 제외 건수 |
| started_at | timestamptz | N | current_timestamp | - | - | 시작 시각 |
| completed_at | timestamptz | Y | - | - | - | 완료 시각 |

### log_cleaning_results (연결 엔티티)
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| cleaning_run_id | uuid | N | - | PK,FK | →log_cleaning_runs(id) ON DELETE CASCADE | 정제 실행 |
| api_log_id | uuid | N | - | PK,FK | →api_request_logs(id) | 원본 로그 |
| is_included | boolean | N | true | - | - | 포함 여부 |
| normalized_endpoint | varchar(255) | Y | - | - | - | 정규화된 경로 |
| normalized_error_code | varchar(50) | Y | - | - | - | 정규화된 에러코드 |
| exclusion_reason | varchar(100) | Y | - | - | CHECK (포함↔사유 null 상호배타) | 제외 사유 |

### api_statistics
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 통계 고유 ID |
| cleaning_run_id | uuid | N | - | FK | →log_cleaning_runs(id) | 기반 정제 실행 |
| period_start | timestamptz | N | - | - | CHECK start<end | 집계 시작 |
| period_end | timestamptz | N | - | - | - | 집계 종료 |
| endpoint | varchar(255) | N | - | - | - | 엔드포인트 |
| http_method | varchar(10) | N | - | - | CHECK IN (...) | HTTP 메서드 |
| request_count | integer | N | 0 | - | CHECK >=0 | 요청 건수 |
| error_count | integer | N | 0 | - | CHECK 0~request_count | 에러 건수 |
| avg_response_time_ms | numeric(12,2) | Y | - | - | CHECK >=0 | 평균 응답시간 |
| p95_response_time_ms | numeric(12,2) | Y | - | - | CHECK >=0 | P95 응답시간 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |
| (복합) | - | - | - | U | UNIQUE(cleaning_run_id, period_start, period_end, endpoint, http_method) | 중복 통계 방지 |

### log_summaries
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 요약 고유 ID |
| requested_by | uuid | N | - | FK | →profiles(id) | 요청자 |
| cleaning_run_id | uuid | N | - | FK | →log_cleaning_runs(id) | 기반 정제 실행 |
| period_start | timestamptz | N | - | - | CHECK start<end | 요약 기간 시작 |
| period_end | timestamptz | N | - | - | - | 요약 기간 종료 |
| filters | jsonb | N | '{}'::jsonb | - | CHECK jsonb_typeof=object | 필터 조건 (의도적 비정규화) |
| summary_text | text | Y | - | - | - | 요약 본문 |
| model_name | varchar(100) | N | - | - | - | 사용 모델 |
| prompt_version | varchar(50) | N | - | - | - | 프롬프트 버전 |
| status | varchar(20) | N | 'running' | - | CHECK IN ('running','succeeded','failed') | 처리 상태 |
| error_code | varchar(50) | Y | - | - | - | 에러 코드 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

### log_summary_evidence (연결 엔티티)
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| summary_id | uuid | N | - | PK,FK | →log_summaries(id) ON DELETE CASCADE | 요약 |
| api_log_id | uuid | N | - | PK,FK | →api_request_logs(id) | 근거 로그 |
| evidence_order | smallint | N | - | - | CHECK >=1 | 근거 제시 순서 |
| claim_text | varchar(500) | Y | - | - | - | 근거 설명 |
| (복합) | - | - | - | U | UNIQUE(summary_id, evidence_order) | 요약 내 근거 제시 순서 중복 방지 |

### summary_evaluation_cases
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 평가 케이스 ID |
| name | varchar(100) | N | - | U | - | 케이스명 |
| period_start | timestamptz | N | - | - | CHECK start<end | 기간 시작 |
| period_end | timestamptz | N | - | - | - | 기간 종료 |
| filters | jsonb | N | '{}'::jsonb | - | CHECK jsonb_typeof=object | 필터 조건 (의도적 비정규화) |
| expected_facts | jsonb | N | - | - | CHECK jsonb_typeof=array | 기대 사실 목록 (의도적 비정규화) |
| scoring_rule_version | varchar(50) | N | - | - | - | 채점 기준 버전 |
| is_active | boolean | N | true | - | - | 활성 여부 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

### improvement_experiments
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 실험 고유 ID |
| name | varchar(100) | N | - | U | - | 실험명 |
| hypothesis | text | N | - | - | - | 가설 |
| change_description | text | N | - | - | - | 변경 내용 |
| before_version | varchar(50) | N | - | - | - | 변경 전 버전 |
| after_version | varchar(50) | N | - | - | - | 변경 후 버전 |
| status | varchar(20) | N | 'planned' | - | CHECK IN ('planned','running','completed','failed') | 실험 상태 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

### summary_evaluation_runs
| 컬럼명 | 타입 | NULL | 기본값 | 키 | 제약조건 | 설명 |
|---|---|---|---|---|---|---|
| id | uuid | N | gen_random_uuid() | PK | - | 실행 고유 ID |
| case_id | uuid | N | - | FK | →summary_evaluation_cases(id) | 평가 케이스 |
| summary_id | uuid | N | - | FK | →log_summaries(id) | 평가 대상 요약 |
| experiment_id | uuid | Y | - | FK | →improvement_experiments(id) | 연계 실험(선택) |
| run_type | varchar(20) | N | - | - | CHECK IN ('baseline','before','after') | 실행 유형 |
| factuality_score | numeric(5,2) | N | - | - | CHECK 0~100 | 사실성 점수 |
| completeness_score | numeric(5,2) | N | - | - | CHECK 0~100 | 완결성 점수 |
| total_score | numeric(5,2) | N | - | - | CHECK 0~100 | 총점 |
| notes | text | Y | - | - | - | 비고 |
| created_at | timestamptz | N | current_timestamp | - | - | 생성일시 |

**로그분석 도메인 인덱스**: `uq_log_summary_evidence_order`(UNIQUE), `idx_api_request_logs_occurred_at`, `idx_api_request_logs_endpoint_occurred_at`, `idx_api_request_logs_status_occurred_at`, `idx_log_cleaning_results_run_included`, `idx_api_statistics_period`, `idx_api_statistics_endpoint_method`, `idx_log_summaries_period`, `idx_log_summaries_status_created_at`, `idx_summary_evaluation_runs_case_created_at`, `idx_summary_evaluation_runs_experiment_type`

---

## 논리 ERD 대조 체크리스트

| 논리 ERD 관계 | 물리 ERD FK | 일치 여부 |
|---|---|---|
| PROFILES ||--o{ CONVERSATIONS | conversations.user_id → profiles(id) | ✅ |
| CONVERSATIONS ||--o{ MESSAGES | messages.conversation_id → conversations(id) | ✅ |
| RESTAURANT_CATEGORIES |o--o{ RESTAURANTS | restaurants.category_id (nullable) → restaurant_categories(id) | ✅ |
| RESTAURANTS ||--o{ MENUS | menus.restaurant_id → restaurants(id) | ✅ |
| TAG_CATEGORIES ||--o{ RESTAURANT_TAGS | restaurant_tags.category_id → tag_categories(id) | ✅ |
| RESTAURANTS/RESTAURANT_TAGS ↔ RESTAURANT_TAG_MAP | restaurant_tag_map 복합PK+FK 2개 | ✅ |
| PROFILES ||--o{ USER_CONSENTS | user_consents.profile_id → profiles(id) | ✅ |
| PROFILES/CONVERSATIONS/RESTAURANTS ||--o{ RECOMMENDATIONS | recommendations 3개 FK | ✅ |
| PROFILES/CONVERSATIONS/RESTAURANTS/RECOMMENDATIONS ||--o{ FEEDBACK | feedback 4개 FK | ✅ |
| PROFILES |o--o{ API_REQUEST_LOGS | api_request_logs.profile_id (nullable) | ✅ |
| LOG_CLEANING_RUNS/API_REQUEST_LOGS ↔ LOG_CLEANING_RESULTS | 복합PK+FK 2개 | ✅ |
| LOG_CLEANING_RUNS ||--o{ API_STATISTICS | api_statistics.cleaning_run_id | ✅ |
| PROFILES/LOG_CLEANING_RUNS ||--o{ LOG_SUMMARIES | log_summaries 2개 FK | ✅ |
| LOG_SUMMARIES/API_REQUEST_LOGS ↔ LOG_SUMMARY_EVIDENCE | 복합PK+FK 2개 | ✅ |
| SUMMARY_EVALUATION_CASES/LOG_SUMMARIES/IMPROVEMENT_EXPERIMENTS ||--o{ SUMMARY_EVALUATION_RUNS | 3개 FK(experiment_id 선택) | ✅ |
| DASHBOARD_* (관계 없음) | FK 없음, 배치 파생 | ✅ |

전체 관계 일치 — 평가기준 ②(논리·물리 ERD 일치) 충족.
