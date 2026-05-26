"""Apollo punch in/out functions."""
from __future__ import annotations

from typing import Any

from auto_punch.apollo.client import Apollo, ApolloError


_PUNCH_PATH = "/backend/pt/api/checkIn/punch/web"


def _punch(client: Apollo, attendance_type: int, override: bool) -> dict:
    data = client.post(
        _PUNCH_PATH,
        json_body={"AttendanceType": attendance_type, "IsOverride": override},
        headers={"functioncode": "PunchCard"},
    )
    payload: dict[str, Any] = (data or {}).get("Data") or {}
    override_message = payload.get("OverrideMessage")
    if override_message:
        # Server returns HTTP 200 with sentinel payload when same-type punch
        # already exists. Surface as business error so callers don't claim success.
        raise ApolloError(override_message)
    return payload


def punch_in(client: Apollo, *, override: bool = False) -> dict:
    return _punch(client, attendance_type=1, override=override)


def punch_out(client: Apollo, *, override: bool = False) -> dict:
    return _punch(client, attendance_type=2, override=override)
