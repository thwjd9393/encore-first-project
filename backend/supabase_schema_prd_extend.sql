-- =========================================================
-- PRD 17.4~17.10 확장 스키마
-- 기존 테이블 CREATE 실행 후 SQL Editor에서 Run
-- 기존 데이터를 지우지 않는다.
--
-- 관련: PRD-BASELINE-1.0 17장, DEC-P16, P1-3, M1~M4
-- kakao_place_id 는 기존 52행에 Kakao ID가 없어 NOT NULL을 걸지 않는다.
-- Kakao 수집 후 ALTER ... SET NOT NULL 로 승격한다.
-- =========================================================

create extension if not exists "pgcrypto";


-- =========================================================
-- 17.4 restaurants
-- =========================================================

alter table restaurants
    add column if not exists kakao_place_id varchar(30),
    add column if not exists kakao_category_name varchar(255),
    add column if not exists lot_address varchar(255),
    add column if not exists road_address varchar(255),
    add column if not exists longitude numeric(10, 7),
    add column if not exists latitude numeric(10, 7),
    add column if not exists kakao_place_url varchar(500),
    add column if not exists business_hours text,
    add column if not exists break_time text,
    add column if not exists source_url varchar(500),
    add column if not exists last_verified_at date,
    add column if not exists is_active boolean not null default true;

alter table restaurants
    alter column storage_path drop not null;

create unique index if not exists uq_restaurants_kakao_place_id
    on restaurants (kakao_place_id)
    where kakao_place_id is not null;

do $$
begin
    alter table restaurants
        add constraint chk_restaurants_longitude
        check (longitude is null or (longitude >= -180 and longitude <= 180));
exception
    when duplicate_object then null;
end $$;

do $$
begin
    alter table restaurants
        add constraint chk_restaurants_latitude
        check (latitude is null or (latitude >= -90 and latitude <= 90));
exception
    when duplicate_object then null;
end $$;


-- =========================================================
-- 17.4 menus
-- =========================================================

alter table menus
    add column if not exists source_url varchar(500),
    add column if not exists last_verified_at date,
    add column if not exists updated_at timestamptz not null default current_timestamp;


-- =========================================================
-- 17.10 conversations soft delete
-- =========================================================

alter table conversations
    add column if not exists deleted_at timestamptz;


-- =========================================================
-- 17.5 user_consents
-- =========================================================

create table if not exists user_consents (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null
        references profiles(id),
    consent_type varchar(30) not null
        check (consent_type in ('terms', 'privacy')),
    consent_version varchar(30) not null,
    is_agreed boolean not null,
    agreed_at timestamptz not null default current_timestamp,
    created_at timestamptz not null default current_timestamp,
    unique (profile_id, consent_type, consent_version)
);


-- =========================================================
-- 17.5 recommendations
-- =========================================================

create table if not exists recommendations (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null unique,
    profile_id uuid not null
        references profiles(id),
    conversation_id uuid not null
        references conversations(id)
        on delete cascade,
    restaurant_id uuid not null
        references restaurants(id),
    conditions jsonb not null default '{}'::jsonb
        check (jsonb_typeof(conditions) = 'object'),
    reason_text varchar(300),
    reason_source varchar(20) not null default 'gemini'
        check (reason_source in ('gemini', 'db_fallback')),
    model_name varchar(100),
    prompt_version varchar(50),
    created_at timestamptz not null default current_timestamp
);


-- =========================================================
-- 17.4 feedback.recommendation_id
-- 기존 평가 행이 있으면 최소 추천 행을 만들어 연결한다.
-- =========================================================

alter table feedback
    add column if not exists recommendation_id uuid;

with inserted as (
    insert into recommendations (
        request_id,
        profile_id,
        conversation_id,
        restaurant_id,
        conditions,
        reason_source
    )
    select
        gen_random_uuid(),
        f.profile_id,
        f.conversation_id,
        f.restaurant_id,
        '{}'::jsonb,
        'db_fallback'
    from feedback f
    where f.recommendation_id is null
    returning id, profile_id, conversation_id, restaurant_id
)
update feedback f
set recommendation_id = i.id
from inserted i
where f.recommendation_id is null
  and i.profile_id = f.profile_id
  and i.conversation_id = f.conversation_id
  and i.restaurant_id = f.restaurant_id;

do $$
begin
    if exists (select 1 from feedback where recommendation_id is null) then
        raise exception 'feedback.recommendation_id backfill failed';
    end if;
end $$;

alter table feedback
    alter column recommendation_id set not null;

do $$
begin
    alter table feedback
        add constraint fk_feedback_recommendation
        foreign key (recommendation_id)
        references recommendations(id)
        on delete cascade;
exception
    when duplicate_object then null;
end $$;

create unique index if not exists uq_feedback_profile_recommendation
    on feedback (profile_id, recommendation_id);

create index if not exists idx_feedback_recommendation_id
    on feedback (recommendation_id);

create index if not exists idx_feedback_profile_created_at
    on feedback (profile_id, created_at desc);


-- =========================================================
-- 17.4 dashboard_search_stats · dashboard_data_quality
-- =========================================================

create unique index if not exists uq_dashboard_search_stats_date_type_key
    on dashboard_search_stats (stat_date, stat_type, stat_key);

alter table dashboard_data_quality
    add column if not exists incomplete_count integer;

update dashboard_data_quality
set incomplete_count = total_restaurant - complete_count
where incomplete_count is null;

alter table dashboard_data_quality
    alter column incomplete_count set default 0;

alter table dashboard_data_quality
    alter column incomplete_count set not null;

do $$
begin
    alter table dashboard_data_quality
        add constraint chk_dashboard_data_quality_counts
        check (complete_count + incomplete_count = total_restaurant);
exception
    when duplicate_object then null;
end $$;


-- =========================================================
-- 17.6 api_request_logs
-- =========================================================

create table if not exists api_request_logs (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null unique,
    profile_id uuid
        references profiles(id)
        on delete set null,
    occurred_at timestamptz not null default current_timestamp,
    http_method varchar(10) not null
        check (http_method in ('GET', 'POST', 'PATCH', 'DELETE')),
    endpoint_path varchar(255) not null,
    status_code smallint not null
        check (status_code >= 100 and status_code <= 599),
    response_time_ms integer not null
        check (response_time_ms >= 0),
    error_code varchar(50),
    client_type varchar(30),
    created_at timestamptz not null default current_timestamp
);

create index if not exists idx_api_request_logs_occurred_at
    on api_request_logs (occurred_at desc);

create index if not exists idx_api_request_logs_endpoint_occurred_at
    on api_request_logs (endpoint_path, occurred_at desc);

create index if not exists idx_api_request_logs_status_occurred_at
    on api_request_logs (status_code, occurred_at desc);


-- =========================================================
-- 17.6 log_cleaning_runs / log_cleaning_results
-- =========================================================

create table if not exists log_cleaning_runs (
    id uuid primary key default gen_random_uuid(),
    period_start timestamptz not null,
    period_end timestamptz not null,
    criteria_version varchar(50) not null,
    status varchar(20) not null default 'running'
        check (status in ('running', 'succeeded', 'failed')),
    source_count integer not null default 0
        check (source_count >= 0),
    included_count integer not null default 0
        check (included_count >= 0),
    excluded_count integer not null default 0
        check (excluded_count >= 0),
    started_at timestamptz not null default current_timestamp,
    completed_at timestamptz,
    check (period_start < period_end)
);

create table if not exists log_cleaning_results (
    cleaning_run_id uuid not null
        references log_cleaning_runs(id)
        on delete cascade,
    api_log_id uuid not null
        references api_request_logs(id),
    is_included boolean not null default true,
    normalized_endpoint varchar(255),
    normalized_error_code varchar(50),
    exclusion_reason varchar(100),
    created_at timestamptz not null default current_timestamp,
    primary key (cleaning_run_id, api_log_id),
    check (
        (is_included = true and exclusion_reason is null)
        or (is_included = false and exclusion_reason is not null)
    )
);

create index if not exists idx_log_cleaning_results_run_included
    on log_cleaning_results (cleaning_run_id, is_included);


-- =========================================================
-- 17.7 api_statistics
-- =========================================================

create table if not exists api_statistics (
    id uuid primary key default gen_random_uuid(),
    cleaning_run_id uuid not null
        references log_cleaning_runs(id),
    period_start timestamptz not null,
    period_end timestamptz not null,
    endpoint varchar(255) not null,
    http_method varchar(10) not null
        check (http_method in ('GET', 'POST', 'PATCH', 'DELETE')),
    request_count integer not null default 0
        check (request_count >= 0),
    error_count integer not null default 0
        check (error_count >= 0 and error_count <= request_count),
    avg_response_time_ms numeric(12, 2)
        check (avg_response_time_ms is null or avg_response_time_ms >= 0),
    p95_response_time_ms numeric(12, 2)
        check (p95_response_time_ms is null or p95_response_time_ms >= 0),
    created_at timestamptz not null default current_timestamp,
    unique (cleaning_run_id, period_start, period_end, endpoint, http_method),
    check (period_start < period_end)
);

create index if not exists idx_api_statistics_period
    on api_statistics (period_start, period_end);

create index if not exists idx_api_statistics_endpoint_method
    on api_statistics (endpoint, http_method);


-- =========================================================
-- 17.8 log_summaries / log_summary_evidence
-- =========================================================

create table if not exists log_summaries (
    id uuid primary key default gen_random_uuid(),
    requested_by uuid not null
        references profiles(id),
    cleaning_run_id uuid not null
        references log_cleaning_runs(id),
    period_start timestamptz not null,
    period_end timestamptz not null,
    filters jsonb not null default '{}'::jsonb
        check (jsonb_typeof(filters) = 'object'),
    summary_text text,
    model_name varchar(100) not null,
    prompt_version varchar(50) not null,
    status varchar(20) not null default 'running'
        check (status in ('running', 'succeeded', 'failed')),
    error_code varchar(50),
    created_at timestamptz not null default current_timestamp,
    check (period_start < period_end)
);

create index if not exists idx_log_summaries_period
    on log_summaries (period_start, period_end);

create index if not exists idx_log_summaries_status_created_at
    on log_summaries (status, created_at desc);

create table if not exists log_summary_evidence (
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
-- 17.9 품질평가·개선 실험
-- =========================================================

create table if not exists summary_evaluation_cases (
    id uuid primary key default gen_random_uuid(),
    name varchar(100) not null unique,
    period_start timestamptz not null,
    period_end timestamptz not null,
    filters jsonb not null default '{}'::jsonb
        check (jsonb_typeof(filters) = 'object'),
    expected_facts jsonb not null
        check (jsonb_typeof(expected_facts) = 'array'),
    scoring_rule_version varchar(50) not null,
    is_active boolean not null default true,
    created_at timestamptz not null default current_timestamp,
    check (period_start < period_end)
);

create table if not exists improvement_experiments (
    id uuid primary key default gen_random_uuid(),
    name varchar(100) not null unique,
    hypothesis text not null,
    change_description text not null,
    before_version varchar(50) not null,
    after_version varchar(50) not null,
    status varchar(20) not null default 'planned'
        check (status in ('planned', 'running', 'completed', 'failed')),
    created_at timestamptz not null default current_timestamp
);

create table if not exists summary_evaluation_runs (
    id uuid primary key default gen_random_uuid(),
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
    created_at timestamptz not null default current_timestamp
);

create index if not exists idx_summary_evaluation_runs_case_created_at
    on summary_evaluation_runs (case_id, created_at desc);

create index if not exists idx_summary_evaluation_runs_experiment_type
    on summary_evaluation_runs (experiment_id, run_type);


-- =========================================================
-- 17.10 추가 인덱스
-- =========================================================

create index if not exists idx_messages_conversation_created_at
    on messages (conversation_id, created_at desc);

create index if not exists idx_recommendations_conversation_created_at
    on recommendations (conversation_id, created_at desc);

create index if not exists idx_recommendations_profile_created_at
    on recommendations (profile_id, created_at desc);

create index if not exists idx_restaurants_is_active
    on restaurants (is_active);
