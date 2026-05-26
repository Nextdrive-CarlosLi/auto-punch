"""Tests for auto_punch.apollo.punch."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from auto_punch.apollo.client import ApolloError
from auto_punch.apollo.punch import punch_in, punch_out


def test_punch_in_posts_correct_payload():
    client = MagicMock()
    client.post.return_value = {"Data": {"punchDate": "2026-05-26T09:03:00+08:00", "LocationName": "office"}}
    result = punch_in(client)
    assert client.post.call_args.kwargs["json_body"] == {"AttendanceType": 1, "IsOverride": False}
    assert result["LocationName"] == "office"


def test_punch_out_uses_attendance_type_2():
    client = MagicMock()
    client.post.return_value = {"Data": {"punchDate": "2026-05-26T18:03:00+08:00"}}
    punch_out(client)
    assert client.post.call_args.kwargs["json_body"]["AttendanceType"] == 2


def test_override_message_raises_apollo_error():
    """The server returns HTTP 200 with OverrideMessage when same-type punch
    already exists today — must be treated as a business error, not success."""
    client = MagicMock()
    client.post.return_value = {"Data": {
        "AttendanceHistoryId": "00000000-0000-0000-0000-000000000000",
        "OverrideMessage": "已有打卡紀錄，是否覆蓋？",
    }}
    with pytest.raises(ApolloError, match="覆蓋"):
        punch_in(client)
