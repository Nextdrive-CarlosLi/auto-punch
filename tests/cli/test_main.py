"""Tests for auto_punch.cli.main."""
from __future__ import annotations

import pytest

from auto_punch.cli.main import main


def test_no_args_prints_help_and_exits_nonzero(capsys):
    rc = main([])
    out = capsys.readouterr()
    assert rc == 2
    assert "usage" in (out.out + out.err).lower()


def test_unknown_subcommand_exits_nonzero():
    with pytest.raises(SystemExit) as exc_info:
        main(["nope"])
    assert exc_info.value.code != 0


def test_run_subcommand_dispatches(monkeypatch):
    called = {}
    def fake_run(args):
        called["type"] = args.type
        return 0
    monkeypatch.setattr("auto_punch.cli.main.run_command", fake_run)
    rc = main(["run", "--type", "in", "--dry-run"])
    assert rc == 0
    assert called["type"] == "in"


def test_status_subcommand_dispatches(monkeypatch):
    monkeypatch.setattr("auto_punch.cli.main.status_command", lambda args: 0)
    assert main(["status"]) == 0


def test_login_subcommand_dispatches(monkeypatch):
    called = {}
    def fake_login(args):
        called["force"] = args.force
        return 0
    monkeypatch.setattr("auto_punch.cli.main.login_command", fake_login)
    main(["login", "--force"])
    assert called["force"] is True
