from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from dotenv import load_dotenv

from app.routes import admin, auth, dashboard, public
from app.routes import my_alerts, account
from core.database import init_db

# Ensure .env values are loaded even if uvicorn is launched without `dotenv run`.
# Use override=True so editing `.env` (and restarting uvicorn) reliably takes effect even if
# older values exist in the environment from a previous shell/session.
load_dotenv(override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(my_alerts.router)
app.include_router(admin.router)
app.include_router(account.router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; connect-src 'self';",
    )
    return response
