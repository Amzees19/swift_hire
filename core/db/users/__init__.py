"""
User-related storage helpers, split by responsibility.
"""
from core.db.users.auth import hash_password, verify_password
from core.db.users.user_store import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    deactivate_user,
    reactivate_user,
    delete_user_data,
    get_deleted_users,
)
from core.db.users.password_reset import (
    create_password_reset_token,
    get_password_reset_token,
    mark_reset_token_used,
    RESET_TOKEN_MINUTES,
)
from core.db.users.sessions import (
    create_session,
    delete_session,
    get_session,
    touch_session,
    SESSION_TIMEOUT_MINUTES,
)
from core.db.users.email_verification import (
    VERIFY_TOKEN_HOURS,
    create_email_verification_token,
    get_email_verification_token,
    mark_email_verification_token_used,
    mark_user_email_verified,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user_password",
    "deactivate_user",
    "reactivate_user",
    "delete_user_data",
    "get_deleted_users",
    "create_password_reset_token",
    "get_password_reset_token",
    "mark_reset_token_used",
    "RESET_TOKEN_MINUTES",
    "create_session",
    "delete_session",
    "get_session",
    "touch_session",
    "SESSION_TIMEOUT_MINUTES",
    "VERIFY_TOKEN_HOURS",
    "create_email_verification_token",
    "get_email_verification_token",
    "mark_email_verification_token_used",
    "mark_user_email_verified",
]
