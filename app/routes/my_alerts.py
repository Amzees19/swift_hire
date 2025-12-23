import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.area_groups import AREA_GROUPS
from app.auth_utils import get_current_user
from app.layout import render_page
from core.database import get_alert_deliveries_for_user

router = APIRouter()


def expand_preferred_locations(raw_pref: str):
    """
    Expand a user's preferred_location string into tokens.

    Kept as a standalone helper for unit tests and consistency with worker matching.
    """
    if not raw_pref:
        return [], False
    tokens = []
    parts = [p.strip() for p in raw_pref.split(";") if p.strip()]
    any_mode = False
    for part in parts:
        lower = part.lower()

        if lower == "any":
            tokens = []
            any_mode = True
            break

        if part in AREA_GROUPS:
            tokens.extend(AREA_GROUPS[part])
            continue
        matched = None
        for label, towns in AREA_GROUPS.items():
            if lower in label.lower():
                matched = label
                break
        if matched:
            tokens.extend(AREA_GROUPS[matched])
        else:
            tokens.append(part)
    tokens = [t.lower() for t in tokens]
    return list(dict.fromkeys(tokens)), any_mode


def _location_matches(tokens: list[str], job_location: str) -> bool:
    """
    Safer matching: compare lowercase tokens against normalized job location.
    - Exact token match against split words
    - Fallback substring check to catch multi-word towns
    """
    if not tokens:
        return False

    job_location_lower = (job_location or "").lower()
    job_tokens = set(re.split(r"[^a-z0-9]+", job_location_lower))
    job_tokens = {t for t in job_tokens if t}

    for tok in tokens:
        if tok in job_tokens:
            return True
        if tok in job_location_lower:
            return True
    return False


def job_matches_subscription(
    job: dict,
    tokens: list[str],
    job_type_pref: str,
    any_mode: bool,
    *,
    subscription_active: bool = True,
) -> bool:
    # Only active subscriptions match
    if not subscription_active:
        return False

    job_location = (job.get("location") or "").lower()
    job_type_str = f"{job.get('type') or ''} {job.get('duration') or ''}".lower()

    if not any_mode:
        if not tokens:
            return False
        if tokens and not _location_matches(tokens, job_location):
            return False

    if job_type_pref and job_type_pref != "any":
        if job_type_pref not in job_type_str:
            return False

    return True


@router.get("/my-alerts", response_class=HTMLResponse)
def my_alerts(request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    deliveries = get_alert_deliveries_for_user(user_id=int(user["id"]), limit=200)

    jobs_rows = ""
    for d in deliveries:
        url = d.get("url") or "#"
        jobs_rows += f"""
        <tr>
          <td>{d.get('job_id')}</td>
          <td>{d.get('title') or ''}</td>
          <td>{d.get('location') or ''}</td>
          <td>{d.get('type') or ''}</td>
          <td>{d.get('duration') or ''}</td>
          <td>{d.get('pay') or ''}</td>
          <td>{d.get('first_seen_at') or ''}</td>
          <td><a href="{url}" target="_blank">View</a></td>
        </tr>
        """

    if not jobs_rows:
        jobs_rows = '<tr><td colspan="8">No alerts yet. You will see jobs here after an alert is generated.</td></tr>'

    body = f"""
    <div class="card">
      <p class="muted">Your alert history (latest first).</p>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Location</th>
            <th>Type</th>
            <th>Duration</th>
            <th>Pay</th>
            <th>First seen</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {jobs_rows}
        </tbody>
      </table>
    </div>
    """

    return render_page("My Alerts – Job Matches", body, user=user)
