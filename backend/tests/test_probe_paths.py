"""Test that probe/sensitive paths return 404 and favicon.ico redirects."""
import pytest
from fastapi.testclient import TestClient

from app.main import app, _is_blocked_probe_path


def test_blocklist_logic():
    assert _is_blocked_probe_path(".env.production") is True
    assert _is_blocked_probe_path(".env") is True
    assert _is_blocked_probe_path(".git/config") is True
    assert _is_blocked_probe_path("wp-admin") is True
    assert _is_blocked_probe_path("config.json") is True
    assert _is_blocked_probe_path("phpmyadmin") is True
    assert _is_blocked_probe_path("login") is False
    assert _is_blocked_probe_path("devices") is False


@pytest.fixture
def client():
    return TestClient(app)


def test_probe_paths_return_404(client: TestClient):
    """Probe paths must return 404, not 200 with index.html."""
    for path in ["/.env.production", "/.env", "/.git/config", "/wp-admin", "/config.json", "/phpmyadmin"]:
        r = client.get(path)
        assert r.status_code == 404, f"GET {path} should be 404, got {r.status_code}"


def test_favicon_ico_redirects(client: TestClient):
    """favicon.ico should redirect to favicon.svg (302), not 200 with index.html."""
    r = client.get("/favicon.ico", follow_redirects=False)
    assert r.status_code == 302, f"GET /favicon.ico should be 302, got {r.status_code}"
    assert r.headers.get("location") == "/favicon.svg"


def test_security_headers_present(client: TestClient):
    """Responses should include X-Content-Type-Options and X-Frame-Options."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
