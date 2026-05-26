"""Query Apollo for today's attendance record + leave/punch helpers."""
from __future__ import annotations

from datetime import date
from typing import Literal

from auto_punch.apollo.client import Apollo


_RECORDS_PATH = "/backend/pt/api/checkinRecords/onOffWork"

LEAVE_KEYWORDS = ("特休", "事假", "病假", "補休", "出差", "公假", "婚假", "喪假")


def fetch_today_record(client: Apollo, today: date) -> dict | None:
    """Return today's row from the personal check-in records, or None."""
    today_str = today.strftime("%Y/%m/%d")
    data = client.get(
        _RECORDS_PATH,
        params={
            "attendanceDateStart": today_str,
            "attendanceDateEnd": today_str,
            "checkInWay": "workOnOff",
            "pageNumber": 1,
            "pageSize": 30,
            "attendanceType": "",
            "departmentId": "",
            "employeeId": "",
            "punchesLocationId": "",
        },
        headers={"functioncode": "PersonalWorkRecords"},
    )
    records = (data or {}).get("Data") or []
    iso_today = today.isoformat()
    for r in records:
        if r.get("AttendanceDate", "").startswith(iso_today):
            return r
    return None


def is_already_punched(record: dict, punch_type: Literal["in", "out"]) -> bool:
    """True if the AttendanceOn field for this slot is set."""
    field = "InAttendanceOn" if punch_type == "in" else "OutAttendanceOn"
    return bool(record.get(field))


def is_on_leave(record: dict, punch_type: Literal["in", "out"]) -> str | None:
    """Return leave-type text if this slot is marked as leave, else None."""
    field = "InTimeoutTypeText" if punch_type == "in" else "OutTimeoutTypeText"
    text = (record.get(field) or "").strip()
    if any(k in text for k in LEAVE_KEYWORDS):
        return text
    return None
