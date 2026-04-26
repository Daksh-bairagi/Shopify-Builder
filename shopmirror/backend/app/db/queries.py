import json
from typing import Any

from app.db.connection import get_pool


def _parse_jsonb(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _to_json(value: Any) -> str:
    return json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

async def create_job(store_url: str, has_token: bool, store_domain: str | None = None) -> str:
    """Insert a new analysis job and return its UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO analysis_jobs (store_url, store_domain, has_token, status, progress_pct)
        VALUES ($1, $2, $3, 'queued', 0)
        RETURNING id::text
        """,
        store_url,
        store_domain,
        has_token,
    )
    return row["id"]


async def update_job_status(
    job_id: str,
    status: str,
    progress_step: str | None = None,
    progress_pct: int | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE analysis_jobs
        SET status        = $2::varchar,
            progress_step = COALESCE($3::varchar, progress_step),
            progress_pct  = COALESCE($4, progress_pct)
        WHERE id = $1::uuid
        """,
        job_id,
        status,
        progress_step,
        progress_pct,
    )


async def update_job_report(
    job_id: str,
    report_json: dict,
    status: str = "complete",
) -> None:
    """Write the audit report. Free tier passes default 'complete'.
    Paid tier passes 'awaiting_approval' — job stays open for fix execution.
    """
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE analysis_jobs
        SET report_json  = $2::jsonb,
            status       = $3::varchar,
            progress_pct = 100,
            completed_at = CASE WHEN $3::text = 'complete' THEN NOW() ELSE NULL END
        WHERE id = $1::uuid
        """,
        job_id,
        _to_json(report_json),
        status,
    )


async def update_job_error(job_id: str, error_message: str) -> None:
    """Mark a job as failed and record the reason."""
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE analysis_jobs
        SET status        = 'failed',
            error_message = $2,
            completed_at  = NOW()
        WHERE id = $1::uuid
        """,
        job_id,
        error_message,
    )


async def patch_report_section(job_id: str, section_key: str, section_value: dict) -> bool:
    """Merge a section into report_json without rewriting the rest. Used by
    on-demand audit endpoints (e.g. ai-visibility) so their results land in the
    same report record the dashboard reads from. Returns True on success."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT report_json FROM analysis_jobs WHERE id = $1::uuid",
        job_id,
    )
    if row is None:
        return False
    existing = _parse_jsonb(row["report_json"]) or {}
    existing[section_key] = section_value
    await pool.execute(
        "UPDATE analysis_jobs SET report_json = $2::jsonb WHERE id = $1::uuid",
        job_id,
        _to_json(existing),
    )
    return True


async def update_job_fix_plan(job_id: str, fix_plan_json: dict) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE analysis_jobs
        SET fix_plan_json = $2::jsonb
        WHERE id = $1::uuid
        """,
        job_id,
        _to_json(fix_plan_json),
    )


async def get_job(job_id: str) -> dict[str, Any] | None:
    """Return the full job row as a dict, or None if not found."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id::text, store_url, store_domain, has_token, status,
               progress_step, progress_pct, report_json, fix_plan_json,
               error_message, created_at, completed_at
        FROM analysis_jobs
        WHERE id = $1::uuid
        """,
        job_id,
    )
    if row is None:
        return None
    result = dict(row)
    result["report_json"] = _parse_jsonb(result.get("report_json"))
    result["fix_plan_json"] = _parse_jsonb(result.get("fix_plan_json"))
    return result


# ---------------------------------------------------------------------------
# Fix backups
# ---------------------------------------------------------------------------

async def save_fix_backup(
    job_id: str,
    fix_id: str,
    product_id: str | None,
    field_type: str,
    field_key: str | None,
    original_value: str | None,
    new_value: str | None,
    shopify_gid: str | None,
    script_tag_id: str | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO fix_backups
            (job_id, fix_id, product_id, field_type, field_key,
             original_value, new_value, shopify_gid, script_tag_id)
        VALUES
            ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        job_id,
        fix_id,
        product_id,
        field_type,
        field_key,
        original_value,
        new_value,
        shopify_gid,
        script_tag_id,
    )


async def get_fix_backup(fix_id: str) -> dict[str, Any] | None:
    """Return the backup row for a fix, or None if not found."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id::text, job_id::text, fix_id, product_id, field_type,
               field_key, original_value, new_value, shopify_gid,
               script_tag_id, applied_at, rolled_back
        FROM fix_backups
        WHERE fix_id = $1
        """,
        fix_id,
    )
    if row is None:
        return None
    return dict(row)


async def mark_fix_rolled_back(fix_id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE fix_backups
        SET rolled_back = TRUE
        WHERE fix_id = $1
        """,
        fix_id,
    )
