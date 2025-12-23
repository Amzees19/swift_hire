from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import re
import os
from typing import Optional

# Optional email/password libraries (not required)
try:
    from email_validator import validate_email, EmailNotValidError  # type: ignore
except ImportError:
    validate_email = None
    class EmailNotValidError(Exception):  # type: ignore
        pass

try:
    from password_strength import PasswordPolicy  # type: ignore
    # password_strength uses specific built-in test names; omit lowercase to avoid KeyError.
    password_policy: Optional[PasswordPolicy] = PasswordPolicy.from_names(
        length=8, numbers=1, uppercase=1, special=0
    )
except ImportError:
    password_policy = None

from app.area_groups import AREA_GROUPS
from app.auth_utils import get_current_user, set_session_cookie
from app.layout import render_page
from app.security import (
    attach_csrf_cookie,
    issue_csrf_token,
    validate_csrf,
    allow_request,
)
from app.email_utils import send_text_email
from core.database import (
    add_subscription,
    create_session,
    create_user,
    create_email_verification_token,
    get_locations,
    get_stats,
    get_user_by_email,
    verify_password,
    reactivate_user,
)


def _build_public_url(request: Request, path: str) -> str:
    base = (os.getenv("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")
    return f"{base}{path}"

router = APIRouter()


def _is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    if not email:
        return False
    # Basic regex (strict) - always enforced
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False
    # Optional deep validation if library is available
    if validate_email:
        try:
            validate_email(email)
        except EmailNotValidError:
            return False
    return True


# Basic rule always enforced: 8-25 chars, at least one letter and one number
def _is_valid_password(pw: str) -> bool:
    pw = (pw or "").strip().replace(" ", "")
    if not pw or len(pw) > 25:
        return False
    if len(pw) < 8:
        return False
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return False
    if password_policy:
        return not password_policy.test(pw)
    return True


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    user, _ = get_current_user(request)

    locations = get_locations()
    options = []

    for label, towns in AREA_GROUPS.items():
        towns_label = ", ".join(towns)
        options.append(f'<option value="{label}">{label} - {towns_label}</option>')

    # Optional "Any" entry to match all locations
    options.append('<option value="Any">Any (all locations)</option>')

    for location in locations:
        label = location["name"]
        code = location.get("code")
        region = location.get("region") or ""
        extra = []
        if code:
            extra.append(code)
        if region:
            extra.append(region)
        if extra:
            label = f"{label} ({', '.join(extra)})"

        options.append(f'<option value="{location["name"]}">{label}</option>')

    options_html = "\n".join(options)

    if user:
        return RedirectResponse(url="/dashboard", status_code=303)

    csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))

    admin_links = ""
    if user and user.get("role") == "admin":
        admin_links = """
        <p class="muted" style="margin-top:1.5rem;">
          Admin views:
          <a href="/subscriptions">📬 subscriptions</a>
          <a href="/jobs">📄 jobs</a>
        </p>
        """
    script_block = """
      <script>
        (function () {
          var style = document.createElement("style");
          style.textContent = ".invalid-field{outline:2px solid #f87171;} .invalid-msg{color:#f87171;font-size:0.85rem;min-height:0.9rem;}";
          document.head.appendChild(style);

          var FORM_KEY = "signup_form_cache_v1";
          var form = document.querySelector('form[action="/subscribe"]');
          if (!form) return;
          form.setAttribute("novalidate", "novalidate");

          var fieldNames = ["email", "preferred_location1", "preferred_location2", "preferred_location3", "job_type"];
          var emailRe = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
          var pwRe = /^(?=.*[A-Za-z])(?=.*\\d)[^\\s]{8,25}$/;

          function flagInvalid(el, msgEl, msg) {
            if (!el) return;
            el.classList.add("invalid-field");
            if (msgEl) msgEl.textContent = msg || "";
          }
          function clearInvalid(el, msgEl) {
            if (!el) return;
            el.classList.remove("invalid-field");
            if (msgEl) msgEl.textContent = "";
          }

          // Restore cached values (sessionStorage clears on tab close)
          try {
            var cached = JSON.parse(sessionStorage.getItem(FORM_KEY) || "{}");
            fieldNames.forEach(function (name) {
              var el = form.elements[name];
              if (el && cached[name]) {
                el.value = cached[name];
              }
            });
          } catch (e) {}

          // Cache on input (excluding passwords)
          form.addEventListener("input", function () {
            var data = {};
            fieldNames.forEach(function (name) {
              var el = form.elements[name];
              if (el && el.value) data[name] = el.value;
            });
            try {
              sessionStorage.setItem(FORM_KEY, JSON.stringify(data));
            } catch (e) {}
          });

          var pw1 = form.elements["password"];
          var pw2 = form.elements["password2"];
          var email = form.elements["email"];

          // Live email validity
          if (email) {
            var msgEmail = form.querySelector('[data-msg-for="email"]');
            var validateEmail = function () {
              if (!email.value) {
                clearInvalid(email, msgEmail);
                return;
              }
              if (!emailRe.test(email.value)) {
                flagInvalid(email, msgEmail, "Enter a valid email address.");
              } else {
                clearInvalid(email, msgEmail);
              }
            };
            email.addEventListener("input", validateEmail);
            validateEmail();
          }

          // Live password validity and match
          var msgPw1 = form.querySelector('[data-msg-for="password"]');
          var msgPw2 = form.querySelector('[data-msg-for="password2"]');
          var enforcePw = function () {
            if (pw1) {
              var raw1 = pw1.value || "";
              var p1 = raw1.replace(/\\s+/g, "");
              pw1.value = p1;
              if (!p1) {
                clearInvalid(pw1, msgPw1);
              } else if (!pwRe.test(p1)) {
                flagInvalid(pw1, msgPw1, "8-25 chars, include a letter and a number.");
              } else {
                clearInvalid(pw1, msgPw1);
              }
            }
            if (pw2) {
              var raw2 = pw2.value || "";
              var p2 = raw2.replace(/\\s+/g, "");
              pw2.value = p2;
              if (!p2) {
                clearInvalid(pw2, msgPw2);
              } else if (!pwRe.test(p2)) {
                flagInvalid(pw2, msgPw2, "8-25 chars, include a letter and a number.");
              } else {
                clearInvalid(pw2, msgPw2);
              }
            }
            if (pw1 && pw2) {
              if (pw1.value && pw2.value && pw1.value !== pw2.value) {
                flagInvalid(pw2, msgPw2, "Passwords do not match.");
              } else if (pw2 && pwRe.test(pw2.value)) {
                if (msgPw2 && msgPw2.textContent === "Passwords do not match.") msgPw2.textContent = "";
                clearInvalid(pw2, msgPw2);
              }
            }
          };
          if (pw1) pw1.addEventListener("input", enforcePw);
          if (pw2) pw2.addEventListener("input", enforcePw);
          enforcePw();

          // Validate on submit (no native tooltips)
          form.addEventListener("submit", function (ev) {
            var firstInvalid = null;
            if (email && !emailRe.test(email.value)) {
              flagInvalid(email, form.querySelector('[data-msg-for="email"]'), "Enter a valid email address.");
              firstInvalid = firstInvalid || email;
            }
            enforcePw();
            if (pw1 && pw2 && pw1.value && pw2.value && pw1.value !== pw2.value) {
              flagInvalid(pw2, form.querySelector('[data-msg-for="password2"]'), "Passwords do not match.");
              firstInvalid = firstInvalid || pw2;
            }
            if (form.querySelector('.invalid-field')) {
              ev.preventDefault();
              if (firstInvalid) firstInvalid.focus();
            }
          });

          // Toggle show/hide passwords
          var toggle = document.getElementById("toggle-show-passwords");
          if (toggle) {
            toggle.addEventListener("change", function () {
              var type = toggle.checked ? "text" : "password";
              if (pw1) pw1.type = type;
              if (pw2) pw2.type = type;
            });
          }
        })();
      </script>
    """

   
  

    body = f"""
      <div class="card form-card">
        <h1>Zone Job Alerts</h1>
        <p class="muted">
          Create an account with email + password and choose up to three preferred areas.
          Start typing, e.g. "Birmingham", "Coventry", "Swansea".
          To match all locations, enter "Any".
        </p>

      <form action="/subscribe" method="post" novalidate>
          <label>
            Email
            <input type="email" name="email" required maxlength="50" />
            <div class="invalid-msg" data-msg-for="email"></div>
          </label>

          <label>
            Password
            <input id="password" type="password" name="password" required maxlength="25" />
            <div class="invalid-msg" data-msg-for="password"></div>
          </label>

          <label>
            Confirm password
            <input id="password2" type="password" name="password2" required maxlength="25" />
            <div class="invalid-msg" data-msg-for="password2"></div>
          </label>

          <label style="display:flex;align-items:center;gap:0.4rem;margin-top:0.5rem;">
            <input type="checkbox" id="toggle-show-passwords"
                   onchange="document.getElementById('password').type=this.checked?'text':'password';document.getElementById('password2').type=this.checked?'text':'password';" />
            <span>Show passwords</span>
          </label>

          <label>
            Preferred location 1
            <input list="locations" name="preferred_location1"
                   placeholder="e.g. Birmingham / Midlands" maxlength="50" />
          </label>

          <label>
            Preferred location 2 (optional)
            <input list="locations" name="preferred_location2"
                   placeholder="e.g. South Wales" maxlength="50" />
          </label>

          <label>
            Preferred location 3 (optional)
            <input list="locations" name="preferred_location3"
                   placeholder="e.g. Glasgow / Edinburgh" maxlength="50" />
          </label>

          <datalist id="locations">
            {options_html}
          </datalist>

          <label>
            Job type / duration
            <select name="job_type">
              <option value="Any">Any</option>
              <option value="Full Time">Full Time</option>
              <option value="Part Time">Part Time</option>
              <option value="Fixed-term">Fixed-term</option>
              <option value="Permanent">Permanent / Regular</option>
              <option value="Regular">Regular (US)</option>
              <option value="Seasonal">Seasonal</option>
            </select>
          </label>

          <label>
            Preferred contract duration
            <select name="job_duration">
              <option value="Any">Any</option>
              <option value="Fixed-term">Fixed-term</option>
              <option value="Permanent">Permanent / Regular</option>
            </select>
          </label>

          <input type="hidden" name="csrf_token" value="{csrf_token}">
          <button type="submit">Start alerts</button>
        </form>

        {admin_links}
      </div>

      {script_block}
    """

    response = render_page("Amazon Job Alerts", body, user)
    attach_csrf_cookie(response, csrf_token)
    return response


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    user, _ = get_current_user(request)
    body = """
    <div class="card form-card">
      <h2>Privacy Policy</h2>
      <p class="muted">
        We use your email only to send job alerts you opt into. Your data is not sold or shared with third parties.
      </p>
      <p class="muted">
        You can deactivate or delete your account at any time from your dashboard. For any questions, contact the admin.
      </p>
    </div>
    """
    return render_page("Privacy", body, user=user)


# ---- Validation (override to ensure latest logic) ----
def _is_valid_email(email: str) -> bool:
    email = (email or "").strip()
    if not email:
        return False
    # Reject punycode/IDNA domains for now
    try:
        domain = email.split("@", 1)[1].lower()
        if domain.startswith("xn--") or ".xn--" in domain:
            return False
    except Exception:
        return False
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False
    if validate_email:
        try:
            # Skip MX/deliverability checks; only validate syntax
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            return False
        except Exception:
            return True
    return True


def _is_valid_password(pw: str) -> bool:
    raw_pw = pw or ""
    if re.search(r"\s", raw_pw):
        return False
    pw = raw_pw.strip()
    if not pw or len(pw) > 25:
        return False
    if len(pw) < 8:
        return False
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return False
    if password_policy:
        return not password_policy.test(pw)
    return True


@router.post("/subscribe")
def subscribe(
    email: str = Form(..., max_length=50),
    password: str = Form(..., max_length=25),
    password2: str = Form(..., max_length=25),
    preferred_location1: str = Form("", max_length=50),
    preferred_location2: str = Form("", max_length=50),
    preferred_location3: str = Form("", max_length=50),
    job_type: str = Form("Any", max_length=30),
    csrf_token: str = Form("", max_length=128),
    request: Request = None,
):
    # Rate limit: 10/5min per IP for subscribe
    ip = request.client.host if request and request.client else "unknown"
    if not allow_request(f"subscribe:{ip}", limit=10, window_seconds=300):
        return HTMLResponse("Too many attempts. Please try again later.", status_code=429)

    if not validate_csrf(request, csrf_token):
        return HTMLResponse("Invalid or missing CSRF token.", status_code=403)

    if not _is_valid_email(email):
        return HTMLResponse(
            content="""
            <html>
              <head><title>Error</title></head>
              <body>
                <h1>Invalid email</h1>
                <p>Please enter a valid email address.</p>
                <p><a href="/">Back to form</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )

    if not _is_valid_password(password):
        return HTMLResponse(
            content="""
            <html>
              <head><title>Error</title></head>
              <body>
                <h1>Password requirements</h1>
                <p>Password must be 8-25 characters and include at least one letter and one number.</p>
                <p><a href="/">Back to form</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )

    if len(email) > 50 or len(password) > 25 or len(password2) > 25:
        return HTMLResponse(
            content="""
            <html>
              <head><title>Error</title></head>
              <body>
                <h1>Input too long</h1>
                <p>Please shorten your email/password and try again.</p>
                <p><a href="/">Back to form</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )
    if password != password2:
        return HTMLResponse(
            content="""
            <html>
              <head><title>Error</title></head>
              <body>
                <h1>Passwords do not match </h1>
                <p><a href="/">Go back</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )

    user = get_user_by_email(email)
    if user is None:
        user_id = create_user(email, password, verified=False)
        verified = False
    else:
        if not verify_password(password, user["password_hash"]):
            return HTMLResponse(
                content="""
                <html>
                  <head><title>Error</title></head>
                  <body>
                    <h1>Account already exists </h1>
                    <p>The email is already registered, but the password is wrong.</p>
                    <p>Please either use the correct password on the form, or log in via
                    <a href="/login">the login page</a>.</p>
                    <p><a href="/">Back to form</a></p>
                  </body>
                </html>
                """,
                status_code=401,
            )
        # Reactivate if previously deactivated
        if not user.get("active"):
            reactivate_user(user["id"])
        user_id = user["id"]
        verified = user.get("email_verified_at") not in (None, "")

    locs = [
        preferred_location1.strip(),
        preferred_location2.strip(),
        preferred_location3.strip(),
    ]
    for l in locs:
        if len(l) > 50:
            return HTMLResponse(
                content="""
                <html>
                  <head><title>Error</title></head>
                  <body>
                    <h1>Preferred location too long</h1>
                    <p>Please keep each location under 50 characters.</p>
                    <p><a href=\"/\">Back to form</a></p>
                  </body>
                </html>
                """,
                status_code=400,
            )
    locs = [l for l in locs if l]
    combined_locations = "; ".join(locs)

    if not verified:
        # Create an inactive subscription until email is verified
        add_subscription(email, combined_locations, job_type, active=0, user_id=user_id)

        token = create_email_verification_token(user_id)
        link = _build_public_url(request, f"/verify-email?token={token}")
        try:
            send_text_email(
                to_email=email,
                subject="Verify your email - Zone Job Alerts",
                body=f"Please verify your email by clicking this link:\n\n{link}\n\nThis link expires in 24 hours.",
            )
        except Exception as e:
            return HTMLResponse(f"Unable to send verification email: {e}", status_code=500)

        body = f"""
        <div class="card form-card">
          <h2>Check your email</h2>
          <p class="muted">
            We sent a verification link to <strong>{email}</strong>.
            Please click the link to activate your alerts.
          </p>
          <p class="muted"><a href="/login">Back to login</a></p>
        </div>
        """
        resp = render_page("Verify your email", body, user=None)
        attach_csrf_cookie(resp, issue_csrf_token(request.cookies.get("csrf_token")))
        return resp

    # Verified users can create active alerts and log in immediately
    add_subscription(email, combined_locations, job_type, active=1, user_id=user_id)

    session_token = create_session(user_id)

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_session_cookie(resp, session_token)
    return resp


@router.get("/health")
def health():
    """
    Basic health check for the app.
    """
    try:
        stats = get_stats()
        return {
            "status": "ok",
            "stats": stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
        }


@router.get("/favicon.ico")
def favicon():
    # Return empty 204 to avoid log noise for missing favicon
    return Response(status_code=204)
