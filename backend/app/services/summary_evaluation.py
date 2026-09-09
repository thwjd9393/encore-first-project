from app.db import supabase
from app.schemas.api_log import EvaluationRunResponse
from app.schemas.common import utc_now
from app.services.log_summary import create_log_summary, get_log_summary, get_log_summary_row

DEFAULT_CASE_NAME = "m6-log-summary-facts"
SCORING_RULE_VERSION = "v1"
DEFAULT_EXPECTED_FACTS = [
    "포함 로그",
    "에러",
    "응답시간",
]
PASS_TOTAL_SCORE = 80.0
PASS_FACTUALITY_SCORE = 80.0


def ensure_default_evaluation_case():
    existing = (
        supabase.table("summary_evaluation_cases")
        .select("id, name, expected_facts, scoring_rule_version, filters")
        .eq("name", DEFAULT_CASE_NAME)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]
    created = (
        supabase.table("summary_evaluation_cases")
        .insert(
            {
                "name": DEFAULT_CASE_NAME,
                "period_start": "2026-01-01T00:00:00Z",
                "period_end": "2026-12-31T23:59:59Z",
                "filters": {
                    "forbidden_facts": ["없는 식당"],
                    "evidence_log_ids": [],
                },
                "expected_facts": DEFAULT_EXPECTED_FACTS,
                "scoring_rule_version": SCORING_RULE_VERSION,
                "is_active": True,
            }
        )
        .execute()
    )
    return (created.data or [None])[0]


def list_active_evaluation_cases():
    result = (
        supabase.table("summary_evaluation_cases")
        .select(
            "id, name, expected_facts, scoring_rule_version, filters, is_active"
        )
        .eq("is_active", True)
        .order("name")
        .execute()
    )
    rows = result.data or []
    if rows:
        return rows
    default_case = ensure_default_evaluation_case()
    return [default_case] if default_case else []


def get_evaluation_case(case_id=None):
    if case_id:
        result = (
            supabase.table("summary_evaluation_cases")
            .select(
                "id, name, expected_facts, scoring_rule_version, filters, is_active"
            )
            .eq("id", str(case_id))
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    cases = list_active_evaluation_cases()
    return cases[0] if cases else None


def parse_case_filters(case_row):
    filters = case_row.get("filters") or {}
    if isinstance(filters, str):
        filters = {}
    forbidden = filters.get("forbidden_facts") or []
    if isinstance(forbidden, str):
        forbidden = [forbidden]
    return forbidden


def calculate_evaluation_scores(
    summary_text,
    expected_facts,
    forbidden_facts=None,
    evidence_items=None,
):
    text = summary_text or ""
    facts = expected_facts or []
    forbidden = forbidden_facts or []
    evidence_items = evidence_items or []
    if isinstance(facts, str):
        facts = [facts]
    if not facts:
        return 0.0, 0.0, 0.0, "정답 사실이 없어 점수를 계산할 수 없습니다."

    matched = [fact for fact in facts if fact in text]
    completeness = round(100.0 * len(matched) / len(facts), 2)
    has_insufficient = "판단할 데이터 부족" in text
    forbidden_hits = [item for item in forbidden if item and item in text]

    if not text.strip():
        factuality = 0.0
        evidence_score = 0.0
        notes = "요약 문장이 없어 사실 일치도를 계산할 수 없습니다."
    elif has_insufficient:
        factuality = 0.0 if forbidden_hits else 100.0
        evidence_score = 100.0 if evidence_items else 0.0
        notes = "데이터 부족 상태를 추측 없이 표시했습니다."
    else:
        if forbidden:
            factuality = round(
                100.0 * (len(forbidden) - len(forbidden_hits)) / len(forbidden),
                2,
            )
        else:
            factuality = 100.0
        evidence_score = 100.0 if evidence_items else 0.0
        notes = (
            f"기대 사실 {len(facts)}개 중 {len(matched)}개 확인. "
            f"금지 사실 {len(forbidden_hits)}건. "
            f"근거 로그 {len(evidence_items)}건."
        )

    total_score = round(
        0.6 * factuality + 0.3 * completeness + 0.1 * evidence_score,
        2,
    )
    passed = (
        total_score >= PASS_TOTAL_SCORE and factuality >= PASS_FACTUALITY_SCORE
    )
    notes = (
        f"{notes} 사실 {factuality}/완전 {completeness}/근거 {evidence_score}/"
        f"총점 {total_score}. 합격 여부: {'합격' if passed else '불합격'}(총점 80·사실 80)."
    )
    return factuality, completeness, total_score, notes


def insert_evaluation_run(
    case_row,
    summary_id,
    summary,
    experiment_id,
    run_type,
):
    expected_facts = case_row.get("expected_facts") or []
    if isinstance(expected_facts, str):
        expected_facts = [expected_facts]
    forbidden_facts = parse_case_filters(case_row)
    factuality, completeness, total_score, notes = calculate_evaluation_scores(
        summary.summary_text,
        expected_facts,
        forbidden_facts=forbidden_facts,
        evidence_items=summary.evidence,
    )
    notes = f"[{case_row.get('name')}] {notes}"
    created = (
        supabase.table("summary_evaluation_runs")
        .insert(
            {
                "case_id": case_row["id"],
                "summary_id": str(summary_id),
                "experiment_id": str(experiment_id) if experiment_id else None,
                "run_type": run_type,
                "factuality_score": factuality,
                "completeness_score": completeness,
                "total_score": total_score,
                "notes": notes,
            }
        )
        .execute()
    )
    return (created.data or [None])[0]


def create_evaluation_run(
    summary_id,
    case_id=None,
    experiment_id=None,
    run_type="baseline",
):
    summary = get_log_summary(summary_id)
    if not summary:
        return None, "RESOURCE_NOT_FOUND"

    if run_type == "after":
        source_row = get_log_summary_row(summary_id)
        if not source_row:
            return None, "RESOURCE_NOT_FOUND"
        summary = create_log_summary(
            summary.period_start,
            summary.period_end,
            source_row["cleaning_run_id"],
            summary.filters,
            prompt_version="v2",
        )
        summary_id = summary.summary_id

    if case_id:
        case_row = get_evaluation_case(case_id)
        if not case_row:
            return None, "RESOURCE_NOT_FOUND"
        cases = [case_row]
    else:
        cases = list_active_evaluation_cases()
        if not cases:
            return None, "RESOURCE_NOT_FOUND"

    last_row = None
    passed_count = 0
    total_sum = 0.0
    for case_row in cases:
        last_row = insert_evaluation_run(
            case_row,
            summary_id,
            summary,
            experiment_id,
            run_type,
        )
        if not last_row:
            return None, "INTERNAL_ERROR"
        total_sum += float(last_row["total_score"])
        if (
            float(last_row["total_score"]) >= PASS_TOTAL_SCORE
            and float(last_row["factuality_score"]) >= PASS_FACTUALITY_SCORE
        ):
            passed_count += 1

    if last_row and len(cases) > 1:
        average_total = round(total_sum / len(cases), 2)
        rollup = (
            f"활성 사례 {len(cases)}건 채점, 합격 {passed_count}건"
            f"(총점 80·사실 80), 평균 총점 {average_total}. "
            f"{last_row.get('notes') or ''}"
        )
        supabase.table("summary_evaluation_runs").update(
            {"notes": rollup}
        ).eq("id", last_row["id"]).execute()
        last_row["notes"] = rollup

    if experiment_id and run_type == "after":
        supabase.table("improvement_experiments").update(
            {"status": "completed"}
        ).eq("id", str(experiment_id)).execute()
        if last_row:
            last_row["notes"] = append_experiment_comparison_notes(
                experiment_id,
                last_row.get("notes") or "",
            )
            supabase.table("summary_evaluation_runs").update(
                {"notes": last_row["notes"]}
            ).eq("id", last_row["id"]).execute()

    return build_evaluation_response(last_row), None


def append_experiment_comparison_notes(experiment_id, notes):
    runs = list_evaluation_runs_by_experiment(experiment_id)
    before_totals = [item.total_score for item in runs if item.run_type == "before"]
    after_totals = [item.total_score for item in runs if item.run_type == "after"]
    before_facts = [item.factuality_score for item in runs if item.run_type == "before"]
    after_facts = [item.factuality_score for item in runs if item.run_type == "after"]
    if not before_totals or not after_totals:
        return notes
    before_avg = round(sum(before_totals) / len(before_totals), 2)
    after_avg = round(sum(after_totals) / len(after_totals), 2)
    before_fact = round(sum(before_facts) / len(before_facts), 2)
    after_fact = round(sum(after_facts) / len(after_facts), 2)
    delta = round(after_avg - before_avg, 2)
    improved = delta >= 5 and after_fact >= before_fact
    conclusion = (
        f"전후 비교: before 총점 평균 {before_avg}, after {after_avg} (차이 {delta}). "
        f"사실 일치 before {before_fact} → after {after_fact}. "
        + (
            "성공 기준(총점 +5·사실 미하락) 충족."
            if improved
            else "성공 기준 미달. 결과를 성공으로 과장하지 않는다."
        )
    )
    return f"{conclusion} {notes}".strip()


def build_evaluation_response(row):
    return EvaluationRunResponse(
        id=row["id"],
        case_id=row["case_id"],
        summary_id=row["summary_id"],
        experiment_id=row.get("experiment_id"),
        run_type=row["run_type"],
        factuality_score=float(row["factuality_score"]),
        completeness_score=float(row["completeness_score"]),
        total_score=float(row["total_score"]),
        notes=row.get("notes"),
        created_at=row.get("created_at") or utc_now(),
    )


def get_evaluation_run(run_id):
    result = (
        supabase.table("summary_evaluation_runs")
        .select(
            "id, case_id, summary_id, experiment_id, run_type, "
            "factuality_score, completeness_score, total_score, notes, created_at"
        )
        .eq("id", str(run_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return build_evaluation_response(rows[0])


def list_evaluation_runs_by_experiment(experiment_id):
    result = (
        supabase.table("summary_evaluation_runs")
        .select(
            "id, case_id, summary_id, experiment_id, run_type, "
            "factuality_score, completeness_score, total_score, notes, created_at"
        )
        .eq("experiment_id", str(experiment_id))
        .order("created_at")
        .execute()
    )
    return [build_evaluation_response(row) for row in result.data or []]
