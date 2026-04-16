import json
from typing import Any

from app.db.connection import get_pool


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
        SET status        = $2,
            progress_step = COALESCE($3, progress_step),
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
            status       = $3,
            progress_pct = 100,
            completed_at = CASE WHEN $3 = 'complete' THEN NOW() ELSE NULL END
        WHERE id = $1::uuid
        """,
        job_id,
        json.dumps(report_json),
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


async def update_job_fix_plan(job_id: str, fix_plan_json: dict) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        UPDATE analysis_jobs
        SET fix_plan_json = $2::jsonb
        WHERE id = $1::uuid
        """,
        job_id,
        json.dumps(fix_plan_json),
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
    return dict(row)


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
               applied_at, rolled_back
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
