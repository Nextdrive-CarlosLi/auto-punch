"""auto-punch status sub-command — today + upcoming weekdays plan."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from auto_punch.apollo.client import Apollo, ApolloAuthError, ApolloError
from auto_punch.apollo.login import LoginError, refresh_cookies
from auto_punch.apollo.records import (
    fetch_today_record, is_already_punched, is_on_leave,
)
from auto_punch.config import MissingConfigError, load_config
from auto_punch.schedule.offset import compute_offset
from auto_punch.schedule.skip import get_holiday_name, is_weekend


TAIPEI = ZoneInfo("Asia/Taipei")
BASELINE_IN = (9, 0)
BASELINE_OUT = (18, 0)
LATE_GRACE_MIN = 10
_DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _target_time(d: date, baseline_hm: tuple[int, int], offset_min: int) -> datetime:
    h, m = baseline_hm
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TAIPEI) + timedelta(minutes=offset_min)


def _fmt_punch_time(iso_str: str | None) -> str:
    if not iso_str:
        return "??:??"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return "??:??"
    return dt.astimezone(TAIPEI).strftime("%H:%M")


def _query_with_refresh(cfg, today):
    """Returns (record_or_None, unreachable_bool)."""
    try:
        client = Apollo(cfg.cookies)
        return fetch_today_record(client, today), False
    except ApolloAuthError:
        pass
    except ApolloError:
        return None, True

    try:
        new_cookies = refresh_cookies()
    except LoginError:
        return None, True

    try:
        client = Apollo(new_cookies)
        return fetch_today_record(client, today), False
    except (ApolloAuthError, ApolloError):
        return None, True


def _status_for(record, ptype, now, target, unreachable):
    if unreachable:
        return "⚠️ apollo unreachable"
    if record:
        leave_text = is_on_leave(record, ptype)
        if leave_text:
            return f"🏖️ leave ({leave_text})"
        if is_already_punched(record, ptype):
            field = "InAttendanceOn" if ptype == "in" else "OutAttendanceOn"
            return f"✅ done @ {_fmt_punch_time(record.get(field))}"
    if now > target + timedelta(minutes=LATE_GRACE_MIN):
        return "⏰ missed"
    return "⏳ scheduled"


def render_today(now, cfg) -> list[str]:
    today = now.date()
    day = _DAY_ABBR[today.weekday()]
    if is_weekend(today):
        return [f"Today: {today} ({day}) — 週末(無打卡)"]
    holiday = get_holiday_name(today)
    if holiday:
        return [f"Today: {today} ({day}) — 國定假日: {holiday}(無打卡)"]

    offset = compute_offset(today, cfg.secret)
    target_in = _target_time(today, BASELINE_IN, offset)
    target_out = _target_time(today, BASELINE_OUT, offset)
    record, unreachable = _query_with_refresh(cfg, today)
    in_status = _status_for(record, "in", now, target_in, unreachable)
    out_status = _status_for(record, "out", now, target_out, unreachable)
    return [
        f"Today: {today} ({day}) | offset={offset:+d}min",
        f"  IN  {target_in.strftime('%H:%M')}  {in_status}",
        f"  OUT {target_out.strftime('%H:%M')}  {out_status}",
    ]


def render_upcoming(start_date, n, secret) -> list[str]:
    lines = ["Upcoming:"]
    d = start_date + timedelta(days=1)
    count = 0
    safety = 0
    while count < n and safety < 365:
        safety += 1
        if not is_weekend(d) and not get_holiday_name(d):
            offset = compute_offset(d, secret)
            t_in = _target_time(d, BASELINE_IN, offset)
            t_out = _target_time(d, BASELINE_OUT, offset)
            day = _DAY_ABBR[d.weekday()]
            lines.append(
                f"  {day} {d.month}/{d.day}: in={t_in.strftime('%H:%M')} "
                f"out={t_out.strftime('%H:%M')} (offset {offset:+d})"
            )
            count += 1
        d += timedelta(days=1)
    return lines


def status_command(args) -> int:
    try:
        cfg = load_config()
    except MissingConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    now = datetime.now(TAIPEI)
    print("\n".join(render_today(now, cfg)))
    print()
    print("\n".join(render_upcoming(now.date(), args.days, cfg.secret)))
    return 0
