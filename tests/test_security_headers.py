import asyncio
from starlette.requests import Request
from starlette.responses import Response

import app.api as api_module


def test_security_headers_applied():
    async def run_test():
        async def call_next(_request: Request) -> Response:
            return Response()

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        resp = await api_module.add_security_headers(request, call_next)

        assert resp.status_code == 200
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "SAMEORIGIN"
        csp = headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src 'self'" in csp

    asyncio.run(run_test())


def test_security_headers_preserve_existing_csp():
    async def run_test():
        async def call_next(_request: Request) -> Response:
            resp = Response()
            resp.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:"
            return resp

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        resp = await api_module.add_security_headers(request, call_next)

        # Existing CSP should not be overridden; other headers still set
        assert resp.headers["Content-Security-Policy"] == "default-src 'self'; img-src 'self' data:"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    asyncio.run(run_test())


def test_security_headers_full_app_with_testclient():
    import pytest as _pytest
    _pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    client = TestClient(api_module.app)
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "default-src 'self'" in (resp.headers.get("Content-Security-Policy") or "")
