"""Pure-Python Apollo OAuth login + BPM SSO handshake.

- No file I/O for credentials — caller passes (company, user, pass).
- BPM handshake runs (server-side session activation requires it),
  but BPM cookies are NOT persisted.
- No Playwright fallback.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from auto_punch.config import load_config, write_config


ASIA_AUTH = "https://asiaauth.mayohr.com"
APOLLO = "https://apollo.mayohr.com"
BPM = "https://bpm.mayohr.com"
REDIRECT_URL = f"{APOLLO}/tube"
BPM_FLOW_URL_PATH = (
    "/backend/fd/api/Authorization/GetFlowUrl"
    "?targetbpm=mayoform&targetPath=bpm%2Fapplyform&lang=zh-tw"
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

_TAIPEI = ZoneInfo("Asia/Taipei")
_CSRF_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')


class LoginError(Exception):
    """OAuth chain or BPM handshake failed."""


def _build_opener() -> tuple[urllib.request.OpenerDirector, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler(),
    )
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "text/html,application/json,*/*"),
        ("Accept-Language", "zh-tw"),
    ]
    return opener, jar


def _get(opener, url, *, accept="*/*"):
    req = urllib.request.Request(url, headers={"Accept": accept})
    try:
        with opener.open(req, timeout=15) as resp:
            return resp.status, resp.read(), resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), url


def _post_form(opener, url, form, *, referer):
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": ASIA_AUTH,
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/plain, */*",
        },
    )
    try:
        with opener.open(req, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _build_cookie_header(jar) -> str:
    parts = []
    for c in jar:
        if c.domain.endswith(".mayohr.com") or c.domain.endswith("mayohr.com"):
            parts.append(f"{c.name}={c.value}")
    return "; ".join(parts)


def _do_bpm_handshake(opener, jar) -> tuple[bool, str]:
    """2-step BPM SSO. Server-side Apollo session activation requires this."""
    flow_url = APOLLO + BPM_FLOW_URL_PATH
    try:
        with opener.open(flow_url, timeout=15) as resp:
            flow_body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return False, f"GetFlowUrl HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"GetFlowUrl network error: {exc}"
    try:
        flow_resp = json.loads(flow_body)
    except json.JSONDecodeError:
        return False, f"GetFlowUrl response not JSON: {flow_body[:200]}"
    sso_url = flow_resp.get("Data") or ""
    if not sso_url.startswith(BPM + "/auth?"):
        return False, f"GetFlowUrl response missing Data SSO URL: {flow_body[:200]}"
    try:
        with opener.open(sso_url, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        return False, f"BPM /auth HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"BPM /auth network error: {exc}"
    has_auth = any(c.name == "auth" and "mayohr.com" in (c.domain or "") for c in jar)
    has_refresh = any(c.name == "refreshToken" and "mayohr.com" in (c.domain or "") for c in jar)
    if not (has_auth and has_refresh):
        return False, "BPM redirect did not Set-Cookie auth/refreshToken"
    return True, "ok"


def do_oauth_login(company_code: str, username: str, password: str) -> str:
    """Run the full Apollo OAuth chain + BPM handshake.

    Returns the Apollo cookie header string on success.
    Raises LoginError on any failure.
    """
    opener, jar = _build_opener()

    # Step 1: GET login → CSRF
    login_url = f"{ASIA_AUTH}/HRM/Account/Login"
    status, body, _ = _get(opener, login_url, accept="text/html,application/xhtml+xml")
    if status != 200:
        raise LoginError(f"Step 1 GET login → HTTP {status}")
    m = _CSRF_RE.search(body.decode("utf-8", errors="replace"))
    if not m:
        raise LoginError("Step 1: __RequestVerificationToken not found in login HTML")
    csrf = m.group(1)

    # Step 2: POST /Token
    token_url = f"{ASIA_AUTH}/Token"
    status, body = _post_form(opener, token_url, {
        "__RequestVerificationToken": csrf,
        "companyCode": company_code,
        "employeeNo": username,
        "userName": f"{company_code}-{username}",
        "password": password,
        "grant_type": "password",
        "locale": "zh-tw",
        "red": REDIRECT_URL,
    }, referer=login_url)
    if status != 200:
        raise LoginError(f"Step 2 POST /Token → HTTP {status}. Wrong credentials or Imperva block.")
    try:
        token_resp = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise LoginError(f"Step 2: response not JSON: {body[:200].decode('utf-8', errors='replace')}")
    code = token_resp.get("code", "")
    if not code:
        raise LoginError(f"Step 2: response has no `code`: {list(token_resp.keys())}")

    # Step 3: GET LoginPass
    loginpass_url = (
        f"{APOLLO}/LoginPass?code={code}"
        f"&red={urllib.parse.quote(REDIRECT_URL, safe='')}&lang=zh-tw"
    )
    status, _, _ = _get(opener, loginpass_url, accept="text/html")
    if status != 200:
        raise LoginError(f"Step 3 GET LoginPass → HTTP {status}")

    # Step 4: GET checkticket
    checkticket_url = f"{APOLLO}/backend/fd/api/auth/checkticket?code={code}"
    status, body, _ = _get(opener, checkticket_url, accept="application/json, text/plain, */*")
    if status != 200:
        raise LoginError(f"Step 4 GET checkticket → HTTP {status}")

    cookie_header = _build_cookie_header(jar)
    if "__ModuleSessionCookie" not in cookie_header:
        raise LoginError(
            "Login chain completed but __ModuleSessionCookie not in jar. "
            "Imperva may have blocked."
        )

    # Step 5: BPM SSO handshake (server-side activation; BPM cookies NOT persisted)
    bpm_ok, bpm_msg = _do_bpm_handshake(opener, jar)
    if not bpm_ok:
        raise LoginError(
            f"BPM handshake failed ({bpm_msg}). Apollo cookies got but HRM "
            "API calls will return 403 until BPM activates the server-side session."
        )

    return cookie_header


def refresh_cookies() -> str:
    """Re-login using credentials from config, write new cookies back to config.

    Returns the new cookie header string. Raises LoginError on failure
    (config.MissingConfigError propagates if .env is missing entirely).
    """
    cfg = load_config()
    cookies = do_oauth_login(cfg.company_code, cfg.username, cfg.password)
    updated_at = datetime.now(_TAIPEI).isoformat(timespec="seconds")
    write_config({
        "APOLLO_COOKIES": cookies,
        "APOLLO_COOKIES_UPDATED_AT": updated_at,
    })
    return cookies
