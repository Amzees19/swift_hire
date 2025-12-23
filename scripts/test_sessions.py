# test_sessions.py
from core.database import (
    init_db,
    create_user,
    get_user_by_email,
    create_session,
    get_session,
    touch_session,
)

init_db()

# ensure a user exists
email = "test@example.com"
user = get_user_by_email(email)
if user is None:
    user_id = create_user(email, "password123")
    user = get_user_by_email(email)

print("User:", user)

token = create_session(user["id"])
print("New session token:", token)

s = get_session(token)
print("Loaded session:", s)
