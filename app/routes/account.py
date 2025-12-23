from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.auth_utils import clear_session_cookie, get_current_user
from core.database import (
    deactivate_user,
    delete_session,
    delete_user_data,
    reactivate_user,
)

router = APIRouter()

@router.post("/account/deactivate")
def deactivate_account(request: Request):
    user, token = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Do not allow admin to deactivate via UI
    if user.get("role") == "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    deactivate_user(user["id"])

    if token:
        delete_session(token)
    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


@router.post("/account/delete")
def delete_account(request: Request):
    user, token = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Do not allow admin to delete via UI
    if user.get("role") == "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    delete_user_data(user["id"])
    if token:
        delete_session(token)
    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


@router.post("/account/reactivate")
def reactivate_account(request: Request):
    user, token = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if user.get("role") == "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    reactivate_user(user["id"])

    # keep existing session if present; otherwise send back to login
    if token:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)
