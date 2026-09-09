-- =========================================================
-- 초기화용 SQL
-- 기존 테이블 삭제 후 전체 재생성
-- 주의: 기존 데이터는 전부 삭제됨
--
-- 붙여넣은 기존 DROP+CREATE 기준.
-- 현재 Supabase public 23개 테이블의 추가 컬럼·테이블을 반영한다.
-- kakao_place_id 는 NOT NULL을 걸지 않는다.
-- =========================================================

create extension if not exists "pgcrypto";


-- =========================================================
-- 0. 테이블 삭제
-- 기존 12개 + 현재 Supabase 추가 11개
-- FK 관계 때문에 자식 테이블부터 삭제
-- =========================================================

drop table if exists summary_evaluation_runs cascade;
drop table if exists summary_evaluation_cases cascade;
drop table if exists improvement_experiments cascade;
drop table if exists log_summary_evidence cascade;
drop table if exists log_summaries cascade;
drop table if exists api_statistics cascade;
drop table if exists log_cleaning_results cascade;
drop table if exists log_cleaning_runs cascade;
drop table if exists api_request_logs cascade;

drop table if exists feedback cascade;
drop table if exists recommendations cascade;
drop table if exists user_consents cascade;
drop table if exists dashboard_search_stats cascade;
drop table if exists dashboard_data_quality cascade;

drop table if exists restaurant_tag_map cascade;
drop table if exists restaurant_tags cascade;
drop table if exists tag_categories cascade;

drop table if exists menus cascade;
drop table if exists restaurants cascade;
drop table if exists restaurant_categories cascade;

drop table if exists messages cascade;
drop table if exists conversations cascade;
drop table if exists profiles cascade;


-- =========================================================
-- 1. 사용자 프로필
-- Supabase auth.users 와 1:1 연결
-- =========================================================

create table profiles (
    id uuid primary key
        references auth.users(id)
        on delete cascade,

    profile_login_id varchar(45)
        unique,

    profile_nickname varchar(45) not null
        unique,

    kakao_profile_id varchar(100)
        unique,

    profile_created_at timestamptz not null
        default current_timestamp,

    profile_updated_at timestamptz,

    profile_withdrawn_at timestamptz,

    profile_status char(1) not null
        default '1'
        check (profile_status in ('0', '1')),

    profile_type char(1) not null
        default '1'
        check (profile_type in ('0', '1'))
);


-- =========================================================
-- 2. 대화방
-- 현재 Supabase 추가: deleted_at
-- =========================================================

create table conversations (
    id uuid primary key
        default gen_random_uuid(),

    user_id uuid not null
        references profiles(id)
        on delete cascade,

    title varchar(100),

    created_at timestamptz not null
        default now(),

    updated_at timestamptz not null
        default now(),

    deleted_at timestamptz
);


-- =========================================================
-- 3. 메시지
-- =========================================================

create table messages (
    id uuid primary key
        default gen_random_uuid(),

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    role varchar(20) not null
        check (role in ('user', 'assistant', 'system')),

    content text not null,

    created_at timestamptz not null
        default now()
);


-- =========================================================
-- 4. 음식점 카테고리
-- =========================================================

create table restaurant_categories (
    id uuid primary key
        default gen_random_uuid(),

    name varchar(30) not null
        unique
);


-- =========================================================
-- 5. 음식점
-- 현재 Supabase 추가: Kakao·주소·좌표·영업시간·출처·is_active
-- storage_path 는 NULL 허용
-- =========================================================

create table restaurants (
    id uuid primary key
        default gen_random_uuid(),

    category_id uuid
        references restaurant_categories(id)
        on delete set null,

    name varchar(100) not null,

    address varchar(255),

    phone varchar(30),

    description varchar(500),

    storage_path varchar(500),

    kakao_place_id varchar(30),

    kakao_category_name varchar(255),

    lot_address varchar(255),

    road_address varchar(255),

    longitude numeric(10, 7)
        check (longitude is null or (longitude >= -180 and longitude <= 180)),

    latitude numeric(10, 7)
        check (latitude is null or (latitude >= -90 and latitude <= 90)),

    kakao_place_url varchar(500),

    business_hours text,

    break_time text,

    source_url varchar(500),

    last_verified_at date,

    is_active boolean not null
        default true,

    created_at timestamptz not null
        default now(),

    updated_at timestamptz not null
        default now()
);


-- =========================================================
-- 6. 메뉴
-- 현재 Supabase 추가: source_url, last_verified_at, updated_at
-- =========================================================

create table menus (
    id uuid primary key
        default gen_random_uuid(),

    restaurant_id uuid not null
        references restaurants(id)
        on delete cascade,

    name varchar(100) not null,

    price integer not null
        check (price >= 0),

    source_url varchar(500),

    last_verified_at date,

    created_at timestamptz not null
        default now(),

    updated_at timestamptz not null
        default current_timestamp
);


-- =========================================================
-- 7. 태그 카테고리
-- 예: 가격대 / 분위기 / 이용목적 / 맛
-- =========================================================

create table tag_categories (
    id uuid primary key
        default gen_random_uuid(),

    code varchar(30) not null
        unique,

    name varchar(30) not null
        unique
);


-- =========================================================
-- 8. 음식점 태그
-- =========================================================

create table restaurant_tags (
    id uuid primary key
        default gen_random_uuid(),

    category_id uuid not null
        references tag_categories(id)
        on delete cascade,

    name varchar(50) not null,

    unique (category_id, name)
);


-- =========================================================
-- 9. 음식점 - 태그 매핑
-- N:M 관계
-- =========================================================

create table restaurant_tag_map (
    restaurant_id uuid not null
        references restaurants(id)
        on delete cascade,

    tag_id uuid not null
        references restaurant_tags(id)
        on delete cascade,

    primary key (restaurant_id, tag_id)
);


-- =========================================================
-- 10. 사용자 동의 (현재 Supabase 추가)
-- =========================================================

create table user_consents (
    id uuid primary key
        default gen_random_uuid(),

    profile_id uuid not null
        references profiles(id),

    consent_type varchar(30) not null
        check (consent_type in ('terms', 'privacy')),

    consent_version varchar(30) not null,

    is_agreed boolean not null,

    agreed_at timestamptz not null
        default current_timestamp,

    created_at timestamptz not null
        default current_timestamp,

    unique (profile_id, consent_type, consent_version)
);


-- =========================================================
-- 11. 추천 결과 (현재 Supabase 추가)
-- =========================================================

create table recommendations (
    id uuid primary key
        default gen_random_uuid(),

    request_id uuid not null
        unique,

    profile_id uuid not null
        references profiles(id),

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    restaurant_id uuid not null
        references restaurants(id),

    conditions jsonb not null
        default '{}'::jsonb
        check (jsonb_typeof(conditions) = 'object'),

    reason_text varchar(300),

    reason_source varchar(20) not null
        default 'gemini'
        check (reason_source in ('gemini', 'db_fallback')),

    model_name varchar(100),

    prompt_version varchar(50),

    created_at timestamptz not null
        default current_timestamp
);


-- =========================================================
-- 12. 추천 피드백
-- 1: 싫어요
-- 2: 중간
-- 3: 좋아요
-- 현재 Supabase 추가: recommendation_id
-- =========================================================

create table feedback (
    feedback_id uuid primary key
        default gen_random_uuid(),

    profile_id uuid not null
        references profiles(id)
        on delete cascade,

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    restaurant_id uuid not null
        references restaurants(id)
        on delete cascade,

    recommendation_id uuid not null
        references recommendations(id)
        on delete cascade,

    feedback_value char(1) not null
        check (feedback_value in ('1', '2', '3')),

    created_at timestamptz not null
        default current_timestamp,

    updated_at timestamptz
);


-- =========================================================
-- 13. 관리자 대시보드 검색 통계
-- stat_type
-- 0: 음식 카테고리
-- 1: 가격대
-- 2: 상황 태그
-- 현재 Supabase 추가: (stat_date, stat_type, stat_key) unique
-- =========================================================

create table dashboard_search_stats (
    stat_id uuid primary key
        default gen_random_uuid(),

    stat_date date not null,

    stat_type char(1) not null
        check (stat_type in ('0', '1', '2')),

    stat_key varchar(45) not null,

    count integer not null
        default 0
        check (count >= 0),

    created_at timestamptz not null
        default current_timestamp,

    unique (stat_date, stat_type, stat_key)
);


-- =========================================================
-- 14. 관리자 대시보드 데이터 품질
-- 현재 Supabase 추가: incomplete_count
-- =========================================================

create table dashboard_data_quality (
    stat_id uuid primary key
        default gen_random_uuid(),

    checked_at timestamptz not null
        default current_timestamp,

    total_restaurant integer not null
        default 0
        check (total_restaurant >= 0),

    complete_count integer not null
        default 0
        check (complete_count >= 0),

    incomplete_count integer not null
        default 0
        check (incomplete_count >= 0),

    check (complete_count + incomplete_count = total_restaurant)
);


-- =========================================================
-- 15. API 원본 로그 (현재 Supabase 추가)
-- =========================================================

create table api_request_logs (
    id uuid primary key
        default gen_random_uuid(),

    request_id uuid not null
        unique,

    profile_id uuid
        references profiles(id)
        on delete set null,

    occurred_at timestamptz not null
        default current_timestamp,

    http_method varchar(10) not null
        check (http_method in ('GET', 'POST', 'PATCH', 'DELETE')),

    endpoint_path varchar(255) not null,

    status_code smallint not null
        check (status_code >= 100 and status_code <= 599),

    response_time_ms integer not null
        check (response_time_ms >= 0),

    error_code varchar(50),

    client_type varchar(30),

    created_at timestamptz not null
        default current_timestamp
);


-- =========================================================
-- 16. 로그 정제 (현재 Supabase 추가)
-- =========================================================

create table log_cleaning_runs (
    id uuid primary key
        default gen_random_uuid(),

    period_start timestamptz not null,

    period_end timestamptz not null,

    criteria_version varchar(50) not null,

    status varchar(20) not null
        default 'running'
        check (status in ('running', 'succeeded', 'failed')),

    source_count integer not null
        default 0
        check (source_count >= 0),

    included_count integer not null
        default 0
        check (included_count >= 0),

    excluded_count integer not null
        default 0
        check (excluded_count >= 0),

    started_at timestamptz not null
        default current_timestamp,

    completed_at timestamptz,

    check (period_start < period_end)
);

create table log_cleaning_results (
    cleaning_run_id uuid not null
        references log_cleaning_runs(id)
        on delete cascade,

    api_log_id uuid not null
        references api_request_logs(id),

    is_included boolean not null
        default true,

    normalized_endpoint varchar(255),

    normalized_error_code varchar(50),

    exclusion_reason varchar(100),

    created_at timestamptz not null
        default current_timestamp,

    primary key (cleaning_run_id, api_log_id),

    check (
        (is_included = true and exclusion_reason is null)
        or (is_included = false and exclusion_reason is not null)
    )
);


-- =========================================================
-- 17. API 통계 (현재 Supabase 추가)
-- =========================================================

create table api_statistics (
    id uuid primary key
        default gen_random_uuid(),

    cleaning_run_id uuid not null
        references log_cleaning_runs(id),

    period_start timestamptz not null,

    period_end timestamptz not null,

    endpoint varchar(255) not null,

    http_method varchar(10) not null
        check (http_method in ('GET', 'POST', 'PATCH', 'DELETE')),

    request_count integer not null
        default 0
        check (request_count >= 0),

    error_count integer not null
        default 0
        check (error_count >= 0 and error_count <= request_count),

    avg_response_time_ms numeric(12, 2)
        check (avg_response_time_ms is null or avg_response_time_ms >= 0),

    p95_response_time_ms numeric(12, 2)
        check (p95_response_time_ms is null or p95_response_time_ms >= 0),

    created_at timestamptz not null
        default current_timestamp,

    unique (cleaning_run_id, period_start, period_end, endpoint, http_method),

    check (period_start < period_end)
);


-- =========================================================
-- 18. LLM 로그 요약과 근거 (현재 Supabase 추가)
-- =========================================================

create table log_summaries (
    id uuid primary key
        default gen_random_uuid(),

    requested_by uuid not null
        references profiles(id),

    cleaning_run_id uuid not null
        references log_cleaning_runs(id),

    period_start timestamptz not null,

    period_end timestamptz not null,

    filters jsonb not null
        default '{}'::jsonb
        check (jsonb_typeof(filters) = 'object'),

    summary_text text,

    model_name varchar(100) not null,

    prompt_version varchar(50) not null,

    status varchar(20) not null
        default 'running'
        check (status in ('running', 'succeeded', 'failed')),

    error_code varchar(50),

    created_at timestamptz not null
        default current_timestamp,

    check (period_start < period_end)
);

create table log_summary_evidence (
    summary_id uuid not null
        references log_summaries(id)
        on delete cascade,

    api_log_id uuid not null
        references api_request_logs(id),

    evidence_order smallint not null
        check (evidence_order >= 1),

    claim_text varchar(500),

    primary key (summary_id, api_log_id)
);


-- =========================================================
-- 19. 요약 품질평가와 개선 실험 (현재 Supabase 추가)
-- =========================================================

create table summary_evaluation_cases (
    id uuid primary key
        default gen_random_uuid(),

    name varchar(100) not null
        unique,

    period_start timestamptz not null,

    period_end timestamptz not null,

    filters jsonb not null
        default '{}'::jsonb
        check (jsonb_typeof(filters) = 'object'),

    expected_facts jsonb not null
        check (jsonb_typeof(expected_facts) = 'array'),

    scoring_rule_version varchar(50) not null,

    is_active boolean not null
        default true,

    created_at timestamptz not null
        default current_timestamp,

    check (period_start < period_end)
);

create table improvement_experiments (
    id uuid primary key
        default gen_random_uuid(),

    name varchar(100) not null
        unique,

    hypothesis text not null,

    change_description text not null,

    before_version varchar(50) not null,

    after_version varchar(50) not null,

    status varchar(20) not null
        default 'planned'
        check (status in ('planned', 'running', 'completed', 'failed')),

    created_at timestamptz not null
        default current_timestamp
);

create table summary_evaluation_runs (
    id uuid primary key
        default gen_random_uuid(),

    case_id uuid not null
        references summary_evaluation_cases(id),

    summary_id uuid not null
        references log_summaries(id),

    experiment_id uuid
        references improvement_experiments(id),

    run_type varchar(20) not null
        check (run_type in ('baseline', 'before', 'after')),

    factuality_score numeric(5, 2) not null
        check (factuality_score >= 0 and factuality_score <= 100),

    completeness_score numeric(5, 2) not null
        check (completeness_score >= 0 and completeness_score <= 100),

    total_score numeric(5, 2) not null
        check (total_score >= 0 and total_score <= 100),

    notes text,

    created_at timestamptz not null
        default current_timestamp
);


-- =========================================================
-- 20. 인덱스
-- =========================================================

create unique index uq_restaurants_kakao_place_id
    on restaurants (kakao_place_id)
    where kakao_place_id is not null;

create unique index uq_feedback_profile_recommendation
    on feedback (profile_id, recommendation_id);

create index idx_conversations_user_id
    on conversations(user_id);

create index idx_messages_conversation_id
    on messages(conversation_id);

create index idx_messages_conversation_created_at
    on messages (conversation_id, created_at desc);

create index idx_restaurants_category_id
    on restaurants(category_id);

create index idx_restaurants_is_active
    on restaurants (is_active);

create index idx_menus_restaurant_id
    on menus(restaurant_id);

create index idx_restaurant_tags_category_id
    on restaurant_tags(category_id);

create index idx_restaurant_tag_map_restaurant_id
    on restaurant_tag_map(restaurant_id);

create index idx_restaurant_tag_map_tag_id
    on restaurant_tag_map(tag_id);

create index idx_feedback_profile_id
    on feedback(profile_id);

create index idx_feedback_conversation_id
    on feedback(conversation_id);

create index idx_feedback_restaurant_id
    on feedback(restaurant_id);

create index idx_feedback_recommendation_id
    on feedback (recommendation_id);

create index idx_feedback_created_at
    on feedback(created_at);

create index idx_feedback_profile_created_at
    on feedback (profile_id, created_at desc);

create index idx_recommendations_conversation_created_at
    on recommendations (conversation_id, created_at desc);

create index idx_recommendations_profile_created_at
    on recommendations (profile_id, created_at desc);

create index idx_dashboard_search_stats_date
    on dashboard_search_stats(stat_date);

create index idx_dashboard_search_stats_type
    on dashboard_search_stats(stat_type);

create index idx_dashboard_search_stats_date_type
    on dashboard_search_stats(stat_date, stat_type);

create index idx_api_request_logs_occurred_at
    on api_request_logs (occurred_at desc);

create index idx_api_request_logs_endpoint_occurred_at
    on api_request_logs (endpoint_path, occurred_at desc);

create index idx_api_request_logs_status_occurred_at
    on api_request_logs (status_code, occurred_at desc);

create index idx_log_cleaning_results_run_included
    on log_cleaning_results (cleaning_run_id, is_included);

create index idx_api_statistics_period
    on api_statistics (period_start, period_end);

create index idx_api_statistics_endpoint_method
    on api_statistics (endpoint, http_method);

create index idx_log_summaries_period
    on log_summaries (period_start, period_end);

create index idx_log_summaries_status_created_at
    on log_summaries (status, created_at desc);

create index idx_summary_evaluation_runs_case_created_at
    on summary_evaluation_runs (case_id, created_at desc);

create index idx_summary_evaluation_runs_experiment_type
    on summary_evaluation_runs (experiment_id, run_type);
