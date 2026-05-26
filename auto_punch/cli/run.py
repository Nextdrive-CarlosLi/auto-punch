"""auto-punch run sub-command — scheduled punch execution."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from auto_punch.apollo.client import Apollo, ApolloAuthError, ApolloError
from auto_punch.apollo.login import LoginError, refresh_cookies
from auto_punch.apollo.punch import punch_in, punch_out
from auto_punch.apollo.records import (
    fetch_today_record, is_already_punched, is_on_leave,
)
from auto_punch.config import MissingConfigError, load_config
from auto_punch.log import log_event
from auto_punch.notify import notify
from auto_punch.schedule.offset import compute_offset
from auto_punch.schedule.skip import get_holiday_name, is_too_late, is_weekend


TAIPEI = ZoneInfo("Asia/Taipei")
BASELINE_IN = (9, 0)
BASELINE_OUT = (18, 0)
LATE_GRACE_MIN = 10


def _log(cfg, **fields):
    try:
        log_event(cfg.log_path, fields)
    except Exception:
        pass  # best-effort


def run_command(args) -> int:
    try:
        cfg = load_config()
    except MissingConfigError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    try:
        return _run(args, cfg)
    except Exception as exc:
        _log(cfg, type=args.type, status="error", reason="unexpected", detail=repr(exc))
        notify("auto-punch", f"未預期錯誤: {exc}", level="error")
        return 1


def _run(args, cfg) -> int:
    ptype = args.type
    now = datetime.now(TAIPEI)
    today = now.date()

    if is_weekend(today):
        _log(cfg, type=ptype, status="skip", reason="weekend")
        return 0

    holiday = get_holiday_name(today)
    if holiday:
        _log(cfg, type=ptype, status="skip", reason="holiday", detail=holiday)
        return 0

    try:
        record = _query_with_refresh(cfg, today, ptype)
    except _AuthFailed:
        return 1

    if record:
        leave = is_on_leave(record, ptype)
        if leave:
            _log(cfg, type=ptype, status="skip", reason="leave", detail=leave)
            return 0
        if is_already_punched(record, ptype):
            _log(cfg, type=ptype, status="skip", reason="already_punched")
            return 0

    offset = compute_offset(today, cfg.secret)
    base_h, base_m = BASELINE_IN if ptype == "in" else BASELINE_OUT
    target = datetime(today.year, today.month, today.day, base_h, base_m, tzinfo=TAIPEI) + timedelta(minutes=offset)

    if args.dry_run:
        print(f"[dry-run] today={today} type={ptype} offset={offset:+d}min target={target.strftime('%H:%M')}")
        return 0

    if is_too_late(now, target, grace_min=LATE_GRACE_MIN):
        _log(cfg, type=ptype, status="error", reason="woke_up_late",
             detail=f"now={now.strftime('%H:%M')} target={target.strftime('%H:%M')}")
        notify("auto-punch",
               f"{target.strftime('%H:%M')} + {LATE_GRACE_MIN}min grace 已過,沒打到",
               level="error")
        return 1

    if now < target:
        time.sleep((target - now).total_seconds())

    return _punch_with_refresh(cfg, ptype, target, offset)


class _AuthFailed(Exception):
    """Sentinel: auth failed even after refresh + retry."""


def _query_with_refresh(cfg, today, ptype):
    """Returns record dict or None. Mutates cfg.cookies if refresh runs.
    Raises _AuthFailed if auth fails twice."""
    try:
        client = Apollo(cfg.cookies)
        return fetch_today_record(client, today)
    except ApolloAuthError as exc:
        _log(cfg, type=ptype, status="warn", reason="refreshing_cookies", detail=f"query: {exc}")
    except ApolloError as exc:
        _log(cfg, type=ptype, status="warn", reason="query_failed", detail=str(exc))
        return None

    try:
        cfg.cookies = refresh_cookies()
    except LoginError as exc2:
        _log(cfg, type=ptype, status="error", reason="refresh_failed", detail=str(exc2))
        notify("auto-punch", f"cookies refresh 失敗: {exc2}", level="error")
        raise _AuthFailed from exc2

    try:
        client = Apollo(cfg.cookies)
        return fetch_today_record(client, today)
    except ApolloAuthError as exc3:
        _log(cfg, type=ptype, status="error", reason="cookies_expired", detail=str(exc3))
        notify("auto-punch", "cookies refresh 後仍失敗,請手動跑 `auto-punch login --force`", level="error")
        raise _AuthFailed from exc3
    except ApolloError as exc3:
        _log(cfg, type=ptype, status="warn", reason="query_failed", detail=str(exc3))
        return None


def _punch_with_refresh(cfg, ptype, target, offset) -> int:
    fn = punch_in if ptype == "in" else punch_out
    try:
        client = Apollo(cfg.cookies)
        try:
            result = fn(client)
        except ApolloAuthError as exc:
            _log(cfg, type=ptype, status="warn", reason="refreshing_cookies", detail=f"punch: {exc}")
            new_cookies = refresh_cookies()
            client = Apollo(new_cookies)
            result = fn(client)
    except ApolloAuthError as exc:
        _log(cfg, type=ptype, status="error", reason="cookies_expired", detail=str(exc))
        notify("auto-punch", "cookies 過期且自動 refresh 失敗,請手動跑 `auto-punch login --force`", level="error")
        return 1
    except LoginError as exc:
        _log(cfg, type=ptype, status="error", reason="refresh_failed", detail=str(exc))
        notify("auto-punch", f"cookies refresh 失敗: {exc}", level="error")
        return 1
    except ApolloError as exc:
        _log(cfg, type=ptype, status="error", reason="business", detail=str(exc))
        notify("auto-punch", f"打卡失敗: {exc}", level="error")
        return 1

    _log(cfg, type=ptype, status="ok", offset=offset, target=target.strftime("%H:%M"),
         location=result.get("LocationName"))
    type_label = "上班" if ptype == "in" else "下班"
    notify("auto-punch", f"✅ {type_label}打卡完成 {target.strftime('%H:%M')}", level="info")
    return 0
