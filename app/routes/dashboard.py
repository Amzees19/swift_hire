from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth_utils import get_current_user
from app.layout import render_page
from app.area_groups import AREA_GROUPS
from core.database import (
    get_all_jobs,
    get_stats,
    get_subscriptions_for_email,
    get_locations,
    update_subscription_for_user,
)

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subs = get_subscriptions_for_email(user["email"])
    # Ensure newest first even if DB ordering changes
    subs = sorted(
        subs,
        key=lambda s: s.get("created_at") or "",
        reverse=True,
    )
    has_active_subs = any(bool(s.get("active")) for s in subs)
    has_inactive_subs = any(not s.get("active") for s in subs)
    stats = get_stats()

    rows_html = ""
    for s in subs:
        status = "Active" if s.get("active") else "Inactive"
        rows_html += f"""
        <tr>
          <td>{s.get('id')}</td>
          <td>{s.get('preferred_location') or ''}</td>
          <td>{s.get('job_type') or ''}</td>
          <td>{status}</td>
          <td>{s.get('created_at') or ''}</td>
        </tr>
        """

    if not rows_html:
        rows_html = '<tr><td colspan="4">No alerts yet. Create one on the home page.</td></tr>'

    admin_stats = ""
    if user.get("role") == "admin":
        admin_stats = f"""
        <div class="stat">
          <div class="label">All active subscriptions</div>
          <div class="value">{stats.get("active_subscriptions", 0)}</div>
        </div>
        <div class="stat">
          <div class="label">Jobs stored</div>
          <div class="value">{stats.get("jobs", 0)}</div>
        </div>
        """

    deactivate_html = ""
    if user.get("role") != "admin":
        # If the account is inactive OR there are no active subs (all inactive), show Reactivate.
        show_reactivate = (not user.get("active")) or (has_inactive_subs and not has_active_subs)
        if show_reactivate:
            deactivate_html = """
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.75rem;">
        <form method="post" action="/account/reactivate">
          <button type="submit" style="background:#22c55e;color:#022c22;border:none;padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;">Reactivate account</button>
        </form>
        <form method="post" action="/account/delete" onsubmit="return confirm('Deletion is not reversible. You will lose access to your account and all alerts. Continue?');">
          <button type="submit" style="background:#f87171;color:#111827;border:none;padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;">Delete account</button>
        </form>
      </div>
            """
        else:
            deactivate_html = """
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.75rem;">
        <form method="post" action="/account/deactivate" onsubmit="return confirm('Deactivate your account? This will stop all alerts.');">
          <button type="submit" style="background:#fbbf24;color:#111827;border:none;padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;">Deactivate account</button>
        </form>
        <form method="post" action="/account/delete" onsubmit="return confirm('Deletion is not reversible. You will lose access to your account and all alerts. Continue?');">
          <button type="submit" style="background:#f87171;color:#111827;border:none;padding:0.5rem 0.75rem;border-radius:6px;cursor:pointer;">Delete account</button>
        </form>
      </div>
            """

    update_options_html = "".join(
        f"<option value='{s.get('id')}' data-loc=\"{s.get('preferred_location') or ''}\" data-job=\"{s.get('job_type') or ''}\">"
        f"{s.get('id')} - {s.get('preferred_location') or ''} ({s.get('job_type') or ''})"
        f"</option>"
        for s in subs
    )
    datalist_options = "".join(
        f"<option value='{label}'></option>"
        for label in list(AREA_GROUPS.keys()) + [loc.get("name") for loc in get_locations()]
    )

    update_form_html = f"""
    <div class="card" style="margin-top:1rem;">
      <p class="muted">Edit a subscription. Click "Edit", adjust fields, then "Save update".</p>
      <button type="button" id="start-edit" style="margin-bottom:0.5rem;">Edit</button>
      <form id="edit-form" method="post" action="/subscription/update" style="display:none;">
        <label>Select alert</label>
        <select name="sub_id" required>
          {update_options_html}
        </select>

        <label>Preferred locations (semicolon separated, or type/pick from list)</label>
        <input list="locations" name="preferred_location" placeholder="e.g. Birmingham / Midlands; London (inner)" required maxlength="50" />

        <datalist id="locations">
          {datalist_options}
        </datalist>

        <label>Job type</label>
        <select name="job_type">
          <option value="Any">Any</option>
          <option value="Full Time">Full Time</option>
          <option value="Part Time">Part Time</option>
          <option value="Fixed-term">Fixed-term</option>
          <option value="Flex Time">Flex Time</option>
        </select>

        <button type="submit" id="save-update" style="margin-top:0.75rem;">Save update</button>
      </form>
    </div>
      <script>
        (function() {{
          var sel = document.querySelector('select[name=\"sub_id\"]');
          var locInput = document.querySelector('input[name=\"preferred_location\"]');
          var jobSelect = document.querySelector('select[name=\"job_type\"]');
          var form = document.getElementById('edit-form');
          var startBtn = document.getElementById('start-edit');
          if (!sel || !locInput || !jobSelect || !form || !startBtn) return;
          var fill = function() {{
            var opt = sel.options[sel.selectedIndex];
            if (!opt) return;
            var loc = opt.getAttribute('data-loc') || '';
            var job = (opt.getAttribute('data-job') || 'Any');
            locInput.value = loc;
            for (var i=0;i<jobSelect.options.length;i++) {{
              if ((jobSelect.options[i].value || '').toLowerCase() === job.toLowerCase()) {{
                jobSelect.selectedIndex = i;
                break;
              }}
            }}
          }};
          sel.addEventListener('change', fill);
          fill();
          startBtn.addEventListener('click', function() {{
            var showing = form.style.display === 'block';
            form.style.display = showing ? 'none' : 'block';
            if (!showing) fill();
          }});
        }})();
      </script>
    """

    body = f"""
    <div class="card" style="margin-bottom:1rem;">
      <div class="muted"><strong>Account created:</strong> {user.get("created_at", "n/a")}</div>
      {deactivate_html}
    </div>

    <div class="stats">
      <div class="stat">
        <div class="label">Your alert subscriptions</div>
        <div class="value">{len(subs)}</div>
      </div>
      {admin_stats}
    </div>

    <div class="card" id="alerts-table">
      <p class="muted">Your alert subscriptions (newest first).</p>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Preferred locations</th>
            <th>Job type</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    {update_form_html}
    """

    return render_page("My Amazon Alerts", body, user=user)


@router.post("/subscription/update")
def update_subscription(request: Request, sub_id: int = Form(...), preferred_location: str = Form(..., max_length=50), job_type: str = Form(..., max_length=30)):
    user, _ = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    success = update_subscription_for_user(sub_id, user["email"], preferred_location.strip(), job_type.strip())
    if not success:
        body = """
        <div class="card">
          <p class="muted">Could not update this alert. It may already be up to date or not require changes.</p>
          <p><a href="/dashboard">Back to dashboard</a></p>
        </div>
        """
        return render_page("Update alert", body, user=user)

    return RedirectResponse(url="/dashboard", status_code=303)
