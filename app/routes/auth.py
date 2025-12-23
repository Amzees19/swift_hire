import os
import smtplib
from email.mime.text import MIMEText
import secrets
import html

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth_utils import clear_session_cookie, get_current_user, set_session_cookie
from app.layout import render_page
from app.security import (
    attach_csrf_cookie,
    issue_csrf_token,
    validate_csrf,
    allow_request,
    allow_request_with_remaining,
)
from app.email_utils import send_text_email
from core.database import (
    create_password_reset_token,
    create_session,
    delete_session,
    create_email_verification_token,
    get_email_verification_token,
    get_password_reset_token,
    get_user_by_id,
    get_user_by_email,
    create_user,
    mark_email_verification_token_used,
    mark_reset_token_used,
    mark_user_email_verified,
    update_user_password,
    verify_password,
    activate_latest_inactive_subscription,
)

router = APIRouter()


def _build_public_url(request: Request, path: str) -> str:
    base = (os.getenv("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")
    return f"{base}{path}"


def _send_verification_email(to_email: str, verify_link: str) -> None:
    send_text_email(
        to_email=to_email,
        subject="Verify your email – Zone Job Alerts",
        body=f"Please verify your email by clicking this link:\n\n{verify_link}\n\nThis link expires in 24 hours.",
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    user, _ = get_current_user(request)
    csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))
    body = f"""
    <div class="card">
      <p class="muted">Log in to view or manage your alerts.</p>
      <form method="post" action="/login">
        <label>Email</label>
        <input type="email" name="email" required maxlength="50" />

        <label>Password</label>
        <input type="password" name="password" required maxlength="25" />

        <input type="hidden" name="csrf_token" value="{csrf_token}" />
        <button type="submit">Login</button>
      </form>
      <p style="margin-top:0.5rem;"><a href="/password-reset">Forgot password?</a></p>
    </div>
    """
    resp = render_page("Login – Amazon Job Alerts", body, user=user)
    attach_csrf_cookie(resp, csrf_token)
    return resp


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(..., max_length=50),
    password: str = Form(..., max_length=25),
    csrf_token: str = Form(""),
):
    ip = request.client.host if request and request.client else "unknown"
    allowed, remaining = allow_request_with_remaining(f"login:{ip}", limit=10, window_seconds=300)
    if not allowed:
        return HTMLResponse("Too many login attempts. Please try again later.", status_code=429)

    if not validate_csrf(request, csrf_token):
        return HTMLResponse("Invalid or missing CSRF token.", status_code=403)

    user = get_user_by_email(email)
    csrf_cookie = request.cookies.get("csrf_token", "")
    safe_email = html.escape(email or "", quote=True)
    attempts_left_html = f"<p class='muted'>Attempts left: {remaining}</p>"

    if not user:
        body = f"""
        <div class="card form-card">
          <p class="muted">Log in to view or manage your alerts.</p>
          <p style="color:#f97373;">Account does not exist for that email.</p>
          {attempts_left_html}
          <p class="muted"><a href="/">Create an account</a></p>
          <form method="post" action="/login">
            <label>Email</label>
            <input type="email" name="email" required maxlength="50" value="{safe_email}" />
            <label>Password</label>
            <input type="password" name="password" required maxlength="25" />
            <input type="hidden" name="csrf_token" value="{csrf_cookie}" />
            <button type="submit">Login</button>
          </form>
          <p style="margin-top:0.5rem;"><a href="/password-reset">Forgot password?</a></p>
        </div>
        """
        return render_page("Login - Amazon Job Alerts", body, user=None)

    if not verify_password(password, user["password_hash"]):
        body = f"""
        <div class="card form-card">
          <p class="muted">Log in to view or manage your alerts.</p>
          <p style="color:#f97373;">Incorrect password. Please try again.</p>
          {attempts_left_html}
          <form method="post" action="/login">
            <label>Email</label>
            <input type="email" name="email" required maxlength="50" value="{safe_email}" />
            <label>Password</label>
            <input type="password" name="password" required maxlength="25" />
            <input type="hidden" name="csrf_token" value="{csrf_cookie}" />
            <button type="submit">Login</button>
          </form>
          <p style="margin-top:0.5rem;"><a href="/password-reset">Forgot password?</a></p>
        </div>
        """
        return render_page("Login - Amazon Job Alerts", body, user=None)

    if user.get("email_verified_at") in (None, ""):
        # Send verification email (rate limit by IP already handled above)
        try:
            token = create_email_verification_token(user["id"])
            link = _build_public_url(request, f"/verify-email?token={token}")
            _send_verification_email(user["email"], link)
        except Exception:
            # Do not leak details; still block login
            pass

        body = """
        <div class="card form-card">
          <h2>Verify your email</h2>
          <p class="muted">
            Your account is not verified yet. Check your inbox for a verification link.
          </p>
          <p class="muted"><a href="/password-reset">Need help?</a></p>
        </div>
        """
        resp = render_page("Verify your email", body, user=None)
        attach_csrf_cookie(resp, issue_csrf_token(request.cookies.get("csrf_token")))
        return resp

    token = create_session(user["id"])
    response = RedirectResponse(url="/dashboard", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/logout")
def logout(request: Request):
    _, token = get_current_user(request)
    if token:
        delete_session(token)
    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


def send_reset_email(to_email: str, reset_link: str) -> None:
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_from = os.getenv("EMAIL_FROM") or email_user or "noreply@zone-alerts.com"
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    # Align From with the authenticated user for Gmail to avoid silent rewrites/blocks.
    if "gmail" in smtp_server.lower() and email_user:
        email_from = email_user

    print(
        "[reset] SMTP config",
        {
            "email_from": email_from,
            "email_user": email_user,
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "has_password": bool(email_password),
        },
    )

    if not (email_from and email_user and email_password):
        raise RuntimeError("Email credentials not configured. Set EMAIL_FROM, EMAIL_USER, EMAIL_PASSWORD.")

    msg = MIMEText(f"Use this link to reset your password:\n\n{reset_link}\n\nIf you did not request this, ignore the email.")
    msg["Subject"] = "Reset your password"
    msg["From"] = email_from
    msg["To"] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_from, [to_email], msg.as_string())


@router.get("/password-reset", response_class=HTMLResponse)
def password_reset_request_form(request: Request):
    user, _ = get_current_user(request)
    csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))
    body = f"""
    <div class="card">
      <p class="muted">Enter your email to get a password reset link.</p>
      <form method="post" action="/password-reset">
        <label>Email</label>
        <input type="email" name="email" required maxlength="50" />
        <input type="hidden" name="csrf_token" value="{csrf_token}" />
        <button type="submit">Send reset link</button>
      </form>
    </div>
    """
    resp = render_page("Reset password", body, user=user)
    attach_csrf_cookie(resp, csrf_token)
    return resp


@router.post("/password-reset", response_class=HTMLResponse)
def password_reset_request(request: Request, email: str = Form(..., max_length=50), csrf_token: str = Form("")):
    ip = request.client.host if request and request.client else "unknown"
    allowed, remaining = allow_request_with_remaining(f"pwdreset:{ip}", limit=5, window_seconds=21600)  # 6 hours
    if not allowed:
        body = """
        <div class="card">
          <p>You have reached the password reset limit (5 per 6 hours).</p>
          <p>Please wait a few hours and try again, or contact the admin for assistance.</p>
          <p><a href="/login">Back to login</a></p>
        </div>
        """
        return HTMLResponse(body, status_code=429)

    if not validate_csrf(request, csrf_token):
        return HTMLResponse("Invalid or missing CSRF token.", status_code=403)
    user = get_user_by_email(email)

    # Admin passwords are managed out-of-band
    if user and user.get("role") == "admin":
        message = "Password reset is not available for this account."
        print(f"[reset] Blocked reset for admin email={email}")
    elif user:
        token = create_password_reset_token(user["id"])
        reset_link = f"{request.url_for('password_reset_confirm')}?token={token}"
        print(f"[reset] Generated token for user_id={user['id']} email={email} link={reset_link}")
        try:
            send_reset_email(email, reset_link)
            print(f"[reset] Sent reset link for user_id={user['id']} email={email}")
            message = "If that email exists, a reset link has been sent."
        except Exception as e:
            print(f"[reset] Failed to send reset link for email={email}: {e}")
            message = f"Unable to send reset email: {e}"
    else:
        print(f"[reset] Reset requested for unknown email={email}")
        message = "If that email exists, a reset link has been sent."

    extra = ""
    if remaining >= 0:
        extra = f"<p class='muted'>You have {remaining} reset attempt(s) left in this 6-hour window.</p>"

    body = f"""
    <div class="card">
      <p>{message}</p>
      {extra}
      <p><a href="/login">Back to login</a></p>
    </div>
    """
    return render_page("Reset password", body, user=None)


@router.get("/password-reset/confirm", response_class=HTMLResponse, name="password_reset_confirm")
def password_reset_confirm_form(request: Request, token: str = ""):
    token_data = get_password_reset_token(token)
    if not token_data:
        body = """
        <div class="card">
          <p>Reset link is invalid or expired.</p>
          <p><a href="/password-reset">Request a new reset link</a></p>
        </div>
        """
        return render_page("Reset password", body, user=None)

    csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))
    body = f"""
    <div class="card">
      <p class="muted">Enter a new password.</p>
      <form method="post" action="/password-reset/confirm?token={token}">
        <label>New password</label>
        <input type="password" name="password" required maxlength="25" />
        <label>Confirm password</label>
        <input type="password" name="password2" required maxlength="25" />
        <input type="hidden" name="csrf_token" value="{csrf_token}" />
        <button type="submit">Set new password</button>
      </form>
    </div>
    """
    resp = render_page("Reset password", body, user=None)
    attach_csrf_cookie(resp, csrf_token)
    return resp


@router.post("/password-reset/confirm", response_class=HTMLResponse)
def password_reset_confirm(
    request: Request,
    token: str = "",
    password: str = Form(..., max_length=25),
    password2: str = Form(..., max_length=25),
    csrf_token: str = Form(""),
):
    ip = request.client.host if request and request.client else "unknown"
    if not allow_request(f"pwdreset_conf:{ip}", limit=5, window_seconds=300):
        return HTMLResponse("Too many attempts. Please try again later.", status_code=429)

    if not validate_csrf(request, csrf_token):
        return HTMLResponse("Invalid or missing CSRF token.", status_code=403)
    token_data = get_password_reset_token(token)
    if not token_data:
        body = """
        <div class="card">
          <p>Reset link is invalid or expired.</p>
          <p><a href="/password-reset">Request a new reset link</a></p>
        </div>
        """
        return render_page("Reset password", body, user=None)

    if password != password2:
        csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))
        body = f"""
        <div class="card">
          <p style="color:#f97373;">Passwords do not match.</p>
          <form method="post" action="/password-reset/confirm?token={token}">
            <label>New password</label>
            <input type="password" name="password" required maxlength="25" />
            <label>Confirm password</label>
            <input type="password" name="password2" required maxlength="25" />
            <input type="hidden" name="csrf_token" value="{csrf_token}" />
            <button type="submit">Set new password</button>
          </form>
        </div>
        """
        resp = render_page("Reset password", body, user=None)
        attach_csrf_cookie(resp, csrf_token)
        return resp

    user_id = token_data["user_id"]
    target_user = get_user_by_id(user_id)
    if not target_user:
        body = """
        <div class="card">
          <p>Reset link is invalid or expired.</p>
          <p><a href="/password-reset">Request a new reset link</a></p>
        </div>
        """
        return render_page("Reset password", body, user=None)

    if target_user.get("role") == "admin":
        body = """
        <div class="card">
          <p>Password reset is not available for this account.</p>
          <p><a href="/login">Back to login</a></p>
        </div>
        """
        return render_page("Reset password", body, user=None)

    update_user_password(user_id, password)
    mark_reset_token_used(token)

    body = """
    <div class="card">
      <p>Password updated. You can now log in.</p>
      <p><a href="/login">Back to login</a></p>
    </div>
    """
    return render_page("Reset password", body, user=None)


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(request: Request, token: str = ""):
    token_data = get_email_verification_token(token)
    if not token_data:
        body = """
        <div class="card form-card">
          <h2>Verification link invalid</h2>
          <p class="muted">This verification link is invalid or expired.</p>
          <p class="muted"><a href="/">Back to signup</a></p>
        </div>
        """
        return render_page("Verify email", body, user=None)

    user = get_user_by_id(token_data["user_id"])
    if not user:
        body = """
        <div class="card form-card">
          <h2>Verification failed</h2>
          <p class="muted">Unable to verify this account.</p>
          <p class="muted"><a href="/">Back to signup</a></p>
        </div>
        """
        return render_page("Verify email", body, user=None)

    # Mark user verified and token used
    mark_user_email_verified(user["id"])
    mark_email_verification_token_used(token)
    # Activate the most recent inactive subscription created during signup
    activate_latest_inactive_subscription(user["email"])

    # Log the user in
    session_token = create_session(user["id"])
    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_session_cookie(resp, session_token)
    return resp


@router.get("/verify-email/resend", response_class=HTMLResponse)
def verify_email_resend_form(request: Request):
    csrf_token = issue_csrf_token(request.cookies.get("csrf_token"))
    body = f"""
    <div class="card form-card">
      <h2>Resend verification email</h2>
      <form method="post" action="/verify-email/resend">
        <label>Email</label>
        <input type="email" name="email" required maxlength="50" />
        <input type="hidden" name="csrf_token" value="{csrf_token}" />
        <button type="submit">Resend</button>
      </form>
    </div>
    """
    resp = render_page("Resend verification", body, user=None)
    attach_csrf_cookie(resp, csrf_token)
    return resp


@router.post("/verify-email/resend", response_class=HTMLResponse)
def verify_email_resend(request: Request, email: str = Form(..., max_length=50), csrf_token: str = Form("")):
    ip = request.client.host if request and request.client else "unknown"
    if not allow_request(f"verify_resend:{ip}", limit=3, window_seconds=3600):
        return HTMLResponse("Too many attempts. Please try again later.", status_code=429)

    if not validate_csrf(request, csrf_token):
        return HTMLResponse("Invalid or missing CSRF token.", status_code=403)

    user = get_user_by_email(email)
    if user and user.get("email_verified_at") in (None, ""):
        try:
            token = create_email_verification_token(user["id"])
            link = _build_public_url(request, f"/verify-email?token={token}")
            _send_verification_email(user["email"], link)
        except Exception:
            pass

    body = """
    <div class="card form-card">
      <p>If that email exists, a verification link has been sent.</p>
      <p class="muted"><a href="/login">Back to login</a></p>
    </div>
    """
    resp = render_page("Resend verification", body, user=None)
    attach_csrf_cookie(resp, issue_csrf_token(request.cookies.get("csrf_token")))
    return resp
