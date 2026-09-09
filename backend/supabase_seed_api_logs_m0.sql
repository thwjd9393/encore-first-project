-- M0: 원본 로그 샘플 3건 (성공 200, 클라이언트 4xx, 서버 5xx).
-- request_id UNIQUE. 기존 행이 있으면 건너뛴다.

insert into api_request_logs (
    request_id,
    occurred_at,
    http_method,
    endpoint_path,
    status_code,
    response_time_ms,
    error_code,
    client_type
) values
(
    '00000000-0000-4000-8000-000000000201',
    '2026-09-08T00:00:01Z',
    'GET',
    '/api/v1/admin/api-logs',
    200,
    42,
    null,
    'streamlit'
),
(
    '00000000-0000-4000-8000-000000000400',
    '2026-09-08T00:00:02Z',
    'GET',
    '/api/v1/admin/api-logs',
    400,
    18,
    'VALIDATION_ERROR',
    'streamlit'
),
(
    '00000000-0000-4000-8000-000000000500',
    '2026-09-08T00:00:03Z',
    'GET',
    '/api/v1/admin/api-statistics/usage',
    500,
    120,
    'INTERNAL_ERROR',
    'streamlit'
)
on conflict (request_id) do nothing;
