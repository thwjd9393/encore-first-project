from app.db import supabase
from app.schemas.api_log import ExperimentResponse
from app.schemas.common import utc_now
from app.services.summary_evaluation import list_evaluation_runs_by_experiment


def create_improvement_experiment(payload):
    created = (
        supabase.table("improvement_experiments")
        .insert(
            {
                "name": payload.name,
                "hypothesis": payload.hypothesis,
                "change_description": payload.change_description,
                "before_version": payload.before_version,
                "after_version": payload.after_version,
                "status": "planned",
            }
        )
        .execute()
    )
    row = (created.data or [None])[0]
    if not row:
        raise RuntimeError("개선 실험을 생성하지 못했습니다.")
    return build_experiment_response(row, [])


def get_improvement_experiment(experiment_id):
    result = (
        supabase.table("improvement_experiments")
        .select(
            "id, name, hypothesis, change_description, before_version, "
            "after_version, status, created_at"
        )
        .eq("id", str(experiment_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    runs = list_evaluation_runs_by_experiment(experiment_id)
    return build_experiment_response(rows[0], runs)


def build_experiment_response(row, runs):
    return ExperimentResponse(
        id=row["id"],
        name=row["name"],
        hypothesis=row["hypothesis"],
        change_description=row["change_description"],
        before_version=row["before_version"],
        after_version=row["after_version"],
        status=row["status"],
        created_at=row.get("created_at") or utc_now(),
        runs=runs,
    )
