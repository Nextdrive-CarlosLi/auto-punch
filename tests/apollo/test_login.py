"""Tests for auto_punch.apollo.login."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from auto_punch.apollo.login import LoginError, do_oauth_login, refresh_cookies


def _csrf_html(token="abc123"):
    return f'<input name="__RequestVerificationToken" value="{token}" />'.encode()


def _resp(status=200, body=b'{"code": "tkt"}'):
    m = MagicMock()
    m.status = status
    m.read.return_value = body
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    m.geturl.return_value = "https://x"
    return m


def test_login_fails_when_csrf_missing():
    with patch("auto_punch.apollo.login.urllib.request.OpenerDirector.open") as op:
        op.return_value = _resp(body=b"no token here")
        with pytest.raises(LoginError, match="RequestVerificationToken"):
            do_oauth_login("acme", "alice", "pw")


def test_refresh_cookies_writes_to_config(env_path, monkeypatch):
    # Pre-populate .env with credentials
    env_path.write_text(
        "APOLLO_COMPANY_CODE=acme\n"
        "APOLLO_USERNAME=alice\n"
        "APOLLO_PASSWORD=pw\n"
        "APOLLO_COOKIES=stale\n"
        "AUTO_PUNCH_SECRET=s\n"
        "AUTO_PUNCH_LOG=/tmp/log.jsonl\n"
    )
    with patch("auto_punch.apollo.login.do_oauth_login", return_value="fresh_cookie=value"):
        result = refresh_cookies()
    assert result == "fresh_cookie=value"
    text = env_path.read_text()
    assert "APOLLO_COOKIES=fresh_cookie=value" in text
    assert "APOLLO_COOKIES_UPDATED_AT=" in text


def test_full_oauth_chain_happy_path(monkeypatch):
    """Mock all 5 HTTP calls + BPM handshake; verify cookie header is returned."""
    call_count = {"n": 0}

    def fake_open(req, timeout=15):
        call_count["n"] += 1
        url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
        m = MagicMock()
        m.__enter__.return_value = m
        m.__exit__.return_value = False
        if "/HRM/Account/Login" in url and "Token" not in url:
            m.status = 200
            m.read.return_value = _csrf_html()
            m.geturl.return_value = url
        elif url.endswith("/Token"):
            m.status = 200
            m.read.return_value = b'{"code": "tkt", "userName": "alice"}'
        elif "/LoginPass" in url:
            m.status = 200
            m.read.return_value = b""
            m.geturl.return_value = url
        elif "/checkticket" in url:
            m.status = 200
            m.read.return_value = b'{"EmployeeId": "E001"}'
            m.geturl.return_value = url
        elif "GetFlowUrl" in url:
            m.status = 200
            m.read.return_value = b'{"Data": "https://bpm.mayohr.com/auth?token=xyz"}'
        elif "bpm.mayohr.com/auth" in url:
            m.status = 200
            m.read.return_value = b""
        else:
            m.status = 200
            m.read.return_value = b""
            m.geturl.return_value = url
        return m

    # Pre-seed jar with required cookies the real BPM handshake would set
    import http.cookiejar

    def fake_build_opener():
        opener = MagicMock()
        jar = http.cookiejar.CookieJar()
        # Simulate Apollo + BPM Set-Cookie responses by inserting cookies directly
        for name in ("__ModuleSessionCookie", "auth", "refreshToken"):
            c = http.cookiejar.Cookie(
                version=0, name=name, value="v", port=None, port_specified=False,
                domain=".mayohr.com", domain_specified=True, domain_initial_dot=True,
                path="/", path_specified=True, secure=True, expires=None,
                discard=False, comment=None, comment_url=None, rest={}, rfc2109=False,
            )
            jar.set_cookie(c)
        opener.open = fake_open
        return opener, jar

    with patch("auto_punch.apollo.login._build_opener", fake_build_opener):
        cookies = do_oauth_login("acme", "alice", "pw")
    assert "__ModuleSessionCookie=" in cookies
    assert "auth=" in cookies
