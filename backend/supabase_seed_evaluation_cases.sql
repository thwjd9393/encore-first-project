-- M6: 성공·에러 급증·지연·데이터 부족을 포함한 평가 사례 10개.
-- forbidden_facts·evidence_log_ids는 기존 filters jsonb에 둔다.

insert into summary_evaluation_cases (
    name, period_start, period_end, filters, expected_facts, scoring_rule_version, is_active
) values
(
    'm6-success-traffic',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"success","forbidden_facts":["없는 식당","원인 미확인 단정"],"evidence_log_ids":[]}'::jsonb,
    '["포함 로그","에러","응답시간"]'::jsonb,
    'v1',
    true
),
(
    'm6-error-spike',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"error_spike","forbidden_facts":["DB가 다운되었다"],"evidence_log_ids":[]}'::jsonb,
    '["에러","4xx","5xx"]'::jsonb,
    'v1',
    true
),
(
    'm6-latency-increase',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"latency","forbidden_facts":["네트워크 장애"],"evidence_log_ids":[]}'::jsonb,
    '["응답시간","p95","엔드포인트"]'::jsonb,
    'v1',
    true
),
(
    'm6-data-insufficient',
    '2026-01-01T00:00:00Z',
    '2026-01-02T00:00:00Z',
    '{"scenario":"insufficient","forbidden_facts":["요청이 급증했다"],"evidence_log_ids":[]}'::jsonb,
    '["판단할 데이터 부족"]'::jsonb,
    'v1',
    true
),
(
    'm6-mixed-4xx-5xx',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"mixed_errors","forbidden_facts":["결제 실패"],"evidence_log_ids":[]}'::jsonb,
    '["에러","상태","포함 로그"]'::jsonb,
    'v1',
    true
),
(
    'm6-usage-endpoints',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"usage","forbidden_facts":["사용자 10만 명"],"evidence_log_ids":[]}'::jsonb,
    '["포함 로그","엔드포인트","사용량"]'::jsonb,
    'v1',
    true
),
(
    'm6-cleaning-excluded',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"cleaning","forbidden_facts":["원본 로그를 삭제했다"],"evidence_log_ids":[]}'::jsonb,
    '["포함 로그","정제"]'::jsonb,
    'v1',
    true
),
(
    'm6-normalized-endpoint',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"normalize","forbidden_facts":["임의의 URL"],"evidence_log_ids":[]}'::jsonb,
    '["엔드포인트","포함 로그"]'::jsonb,
    'v1',
    true
),
(
    'm6-error-code-unify',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"error_code","forbidden_facts":["토큰이 유출되었다"],"evidence_log_ids":[]}'::jsonb,
    '["에러 코드","에러"]'::jsonb,
    'v1',
    true
),
(
    'm6-include-count',
    '2026-09-01T00:00:00Z',
    '2026-09-08T23:59:59Z',
    '{"scenario":"counts","forbidden_facts":["원인 미상 장애"],"evidence_log_ids":[]}'::jsonb,
    '["포함 로그","에러","응답시간"]'::jsonb,
    'v1',
    true
)
on conflict (name) do update
set
    period_start = excluded.period_start,
    period_end = excluded.period_end,
    filters = excluded.filters,
    expected_facts = excluded.expected_facts,
    scoring_rule_version = excluded.scoring_rule_version,
    is_active = excluded.is_active;

update summary_evaluation_cases
set is_active = false
where name = 'm6-log-summary-facts';
