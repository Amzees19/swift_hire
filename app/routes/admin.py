from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timezone

from app.auth_utils import get_current_user
from app.layout import render_page
from core.database import (
    deactivate_subscription,
    get_active_subscriptions,
    get_deleted_subscriptions,
    get_deleted_users,
    get_all_jobs,
)

router = APIRouter()


def _format_dt(dt_str: str | None) -> str:
    """Render ISO timestamp as local human-readable string."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str or ""


@router.get("/jobs", response_class=HTMLResponse)
def list_jobs(request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "admin":
        return HTMLResponse("Forbidden", status_code=403)
    jobs = get_all_jobs(limit=100)

    rows_html = ""
    for j in jobs:
        url = j.get("url") or "#"
        rows_html += f"""
        <tr>
          <td>{j.get('id')}</td>
          <td>{j.get('title') or ''}</td>
          <td>{j.get('location') or ''}</td>
          <td>{j.get('type') or ''}</td>
          <td>{j.get('duration') or ''}</td>
          <td>{j.get('pay') or ''}</td>
          <td>{_format_dt(j.get('first_seen_at'))}</td>
          <td><a href="{url}" target="_blank">View</a></td>
        </tr>
        """

    if not jobs:
        rows_html = '<tr><td colspan="8">No jobs stored yet.</td></tr>'

    body = f"""
    <div class="card">
      <h2>Stored jobs</h2>
      <p class="muted">
        Showing the most recent {len(jobs)} jobs currently in the database.
      </p>
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
          {rows_html}
        </tbody>
      </table>
    </div>
    """

    return render_page("Stored Jobs – Amazon Job Alerts", body, user=user)


@router.get("/subscriptions", response_class=HTMLResponse)
def list_subscriptions(request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "admin":
        return HTMLResponse("Forbidden", status_code=403)
    subs = get_active_subscriptions()

    rows_html = ""
    for s in subs:
        rows_html += f"""
        <tr>
          <td>{s.get('id')}</td>
          <td>{s.get('email')}</td>
          <td>{s.get('preferred_location') or ''}</td>
          <td>{s.get('job_type') or ''}</td>
          <td>
            <a href="/subscriptions/{s.get('id')}/deactivate"
               onclick="return confirm('Deactivate this subscription?');">
               Deactivate
            </a>
          </td>
        </tr>
        """

    if not subs:
        rows_html = '<tr><td colspan="5">No active subscriptions.</td></tr>'

    body = f"""
    <div class="card">
      <h2>Active Subscriptions</h2>
      <p class="muted"><a href="/archives">View deleted records</a></p>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>Preferred locations</th>
            <th>Job type</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
      </table>
    </div>
    """

    return render_page("Subscriptions – Amazon Job Alerts", body, user=user)


@router.get("/subscriptions/{sub_id}/deactivate")
def deactivate_subscription_route(sub_id: int, request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "admin":
        return HTMLResponse("Forbidden", status_code=403)

    deactivate_subscription(sub_id)
    return RedirectResponse(url="/subscriptions", status_code=303)


@router.get("/archives", response_class=HTMLResponse)
def list_archives(request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user.get("role") != "admin":
        return HTMLResponse("Forbidden", status_code=403)

    deleted_users = get_deleted_users(limit=100)
    deleted_subs = get_deleted_subscriptions(limit=200)

    users_html = ""
    for u in deleted_users:
        users_html += f"""
        <tr>
          <td>{u.get('user_id')}</td>
          <td>{u.get('email')}</td>
          <td>{u.get('role')}</td>
          <td>{_format_dt(u.get('created_at'))}</td>
          <td>{_format_dt(u.get('deleted_at'))}</td>
        </tr>
        """
    if not deleted_users:
        users_html = '<tr><td colspan="5">No deleted users.</td></tr>'

    subs_html = ""
    for s in deleted_subs:
        subs_html += f"""
        <tr>
          <td>{s.get('subscription_id')}</td>
          <td>{s.get('user_id') or ''}</td>
          <td>{s.get('email')}</td>
          <td>{s.get('preferred_location') or ''}</td>
          <td>{s.get('job_type') or ''}</td>
          <td>{_format_dt(s.get('created_at'))}</td>
          <td>{_format_dt(s.get('deleted_at'))}</td>
        </tr>
        """
    if not deleted_subs:
        subs_html = '<tr><td colspan="7">No deleted subscriptions.</td></tr>'

    body = f"""
    <div class="card">
      <h2>Deleted users</h2>
      <table>
        <thead>
          <tr>
            <th>User ID</th>
            <th>Email</th>
            <th>Role</th>
            <th>Created</th>
            <th>Deleted</th>
          </tr>
        </thead>
        <tbody>
          {users_html}
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top:1rem;">
      <h2>Deleted subscriptions</h2>
      <table>
        <thead>
          <tr>
            <th>Subscription ID</th>
            <th>User ID</th>
            <th>Email</th>
            <th>Preferred locations</th>
            <th>Job type</th>
            <th>Created</th>
            <th>Deleted</th>
          </tr>
        </thead>
        <tbody>
          {subs_html}
        </tbody>
      </table>
    </div>
    """

    return render_page("Archives – Amazon Job Alerts", body, user=user)
