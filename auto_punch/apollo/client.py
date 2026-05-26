"""Apollo HR API client. Pure HTTP wrapper around urllib + cookies passed in."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, NoReturn


BASE_URL = "https://apollo.mayohr.com"

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-tw",
    "actioncode": "Default",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
}


class ApolloAuthError(Exception):
    """Cookies absent or invalid. Caller should refresh + retry once."""


class ApolloError(Exception):
    """Other API / network errors. Not auth-related."""


class Apollo:
    def __init__(self, cookies: str):
        if not cookies:
            raise ApolloAuthError("cookies empty; run `auto-punch login`")
        self.cookies = cookies

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return self._request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return self._request("POST", path, json_body=json_body, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = BASE_URL + path
        if params:
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)

        merged_headers = dict(DEFAULT_HEADERS)
        merged_headers["cookie"] = self.cookies
        if headers:
            merged_headers.update(headers)

        if method not in ("GET", "HEAD"):
            merged_headers.setdefault("origin", BASE_URL)
            merged_headers.setdefault("referer", BASE_URL + "/")
            merged_headers.setdefault("x-requested-with", "XMLHttpRequest")

        data: bytes | None = None
        if json_body is not None:
            merged_headers["content-type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url, data=data, method=method, headers=merged_headers
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return self._parse_response(resp.status, resp.read(), resp.geturl())
        except urllib.error.HTTPError as exc:
            body = exc.read()
            self._raise_for_status(exc.code, body, exc.headers.get("Location") if exc.headers else None)
        except urllib.error.URLError as exc:
            raise ApolloError(f"Network error contacting {url}: {exc}") from exc
        except ValueError as exc:
            raise ApolloError(f"Malformed request headers (check cookies): {exc}") from exc

    @staticmethod
    def _parse_response(status: int, body: bytes, final_url: str) -> Any:
        if urllib.parse.urlparse(final_url).path.startswith("/HRM/Account/Login"):
            raise ApolloAuthError(
                "Cookies expired or invalid (redirected to login). "
                "Will be refreshed automatically."
            )
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            preview = body[:500].decode("utf-8", errors="replace")
            raise ApolloError(
                f"Non-JSON response (HTTP {status}): {preview}"
            ) from exc

    @staticmethod
    def _extract_server_error(body: bytes) -> tuple[str, str]:
        preview = body.decode("utf-8", errors="replace")[:500]
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "", preview
        err = data.get("Error") if isinstance(data, dict) else None
        if not isinstance(err, dict):
            return "", preview
        title = (err.get("Title") or "").strip()
        status_str = (err.get("Status") or "").strip()
        if title and status_str:
            return f"{status_str}: {title}", preview
        return title or status_str, preview

    @classmethod
    def _raise_for_status(cls, status: int, body: bytes, location: str | None) -> NoReturn:
        title, preview = cls._extract_server_error(body)
        _ACCESS_DENIED_CODES = {"sh_noauthorizationtoaccess"}
        title_code = title.split(":")[0].strip().lower()
        is_auth = (
            status == 401 and title_code not in _ACCESS_DENIED_CODES
        ) or (
            status == 403
            and ("token" in title.lower() or "[invalid]" in title.lower())
        )
        if is_auth:
            detail = f": {title}" if title else ""
            raise ApolloAuthError(
                f"Cookies expired or invalid (HTTP {status}{detail})."
            )
        if title:
            raise ApolloError(f"HTTP {status}: {title}")
        raise ApolloError(f"HTTP {status}: {preview}")
