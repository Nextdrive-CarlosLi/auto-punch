"""Tests for auto_punch.apollo.client."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from auto_punch.apollo.client import Apollo, ApolloAuthError, ApolloError


def _resp(status=200, body=b'{"ok": true}', final_url="https://apollo.mayohr.com/x"):
    m = MagicMock()
    m.status = status
    m.read.return_value = body
    m.geturl.return_value = final_url
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


def test_get_returns_parsed_json():
    client = Apollo(cookies="k=v")
    with patch("auto_punch.apollo.client.urllib.request.urlopen", return_value=_resp()):
        data = client.get("/path")
    assert data == {"ok": True}


def test_redirect_to_login_raises_auth_error():
    client = Apollo(cookies="k=v")
    fake = _resp(final_url="https://asiaauth.mayohr.com/HRM/Account/Login")
    with patch("auto_punch.apollo.client.urllib.request.urlopen", return_value=fake):
        with pytest.raises(ApolloAuthError, match="expired"):
            client.get("/path")


def test_401_raises_auth_error():
    client = Apollo(cookies="k=v")
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://apollo.mayohr.com/x", code=401,
        msg="Unauthorized", hdrs=None, fp=io.BytesIO(b'{}'),
    )
    with patch("auto_punch.apollo.client.urllib.request.urlopen", side_effect=err):
        with pytest.raises(ApolloAuthError):
            client.get("/path")


def test_403_token_gone_raises_auth_error():
    client = Apollo(cookies="k=v")
    import urllib.error
    body = json.dumps({"Error": {"Title": "[Invalid] Token is gone or invalid."}}).encode()
    err = urllib.error.HTTPError(
        url="https://apollo.mayohr.com/x", code=403,
        msg="Forbidden", hdrs=None, fp=io.BytesIO(body),
    )
    with patch("auto_punch.apollo.client.urllib.request.urlopen", side_effect=err):
        with pytest.raises(ApolloAuthError, match="Token"):
            client.get("/path")


def test_403_access_denied_raises_apollo_error_not_auth_error():
    """sh_noauthorizationtoaccess means permission/IP-block, not cookie expiry."""
    client = Apollo(cookies="k=v")
    import urllib.error
    body = json.dumps({"Error": {"Title": "Access denied", "Status": "sh_noauthorizationtoaccess"}}).encode()
    err = urllib.error.HTTPError(
        url="https://apollo.mayohr.com/x", code=401,
        msg="Unauthorized", hdrs=None, fp=io.BytesIO(body),
    )
    with patch("auto_punch.apollo.client.urllib.request.urlopen", side_effect=err):
        with pytest.raises(ApolloError) as exc_info:
            client.get("/path")
        assert not isinstance(exc_info.value, ApolloAuthError)


def test_500_raises_apollo_error():
    client = Apollo(cookies="k=v")
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://apollo.mayohr.com/x", code=500,
        msg="ISE", hdrs=None, fp=io.BytesIO(b"oops"),
    )
    with patch("auto_punch.apollo.client.urllib.request.urlopen", side_effect=err):
        with pytest.raises(ApolloError):
            client.get("/path")


def test_post_sends_json_body():
    client = Apollo(cookies="k=v")
    with patch("auto_punch.apollo.client.urllib.request.urlopen", return_value=_resp()) as urlopen:
        client.post("/x", json_body={"a": 1})
    req = urlopen.call_args[0][0]
    assert req.data == b'{"a": 1}'
    assert req.get_header("Content-type") == "application/json"
