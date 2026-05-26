"""Tests for auto_punch.cli.launchd."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_launchagents(tmp_path, monkeypatch):
    d = tmp_path / "LaunchAgents"
    d.mkdir()
    monkeypatch.setattr("auto_punch.cli.launchd.LAUNCH_AGENTS_DIR", d)
    return d


def test_install_writes_two_plists(env_path, fake_launchagents):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\n"
        f"AUTO_PUNCH_LOG={env_path.parent / 'x.log'}\n"
    )
    from auto_punch.cli.launchd import install_launchd_command
    with patch("auto_punch.cli.launchd.shutil.which", return_value="/usr/local/bin/auto-punch"), \
         patch("auto_punch.cli.launchd.subprocess.run") as run_mock, \
         patch("auto_punch.cli.launchd._smoke_test", return_value=True):
        rc = install_launchd_command(SimpleNamespace())
    assert rc == 0
    plists = list(fake_launchagents.glob("com.carlos.auto-punch.*.plist"))
    assert len(plists) == 2
    morning = (fake_launchagents / "com.carlos.auto-punch.morning.plist").read_text()
    assert "/usr/local/bin/auto-punch" in morning
    assert "{{CLI_PATH}}" not in morning


def test_install_aborts_when_cli_not_found(env_path, fake_launchagents):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.launchd import install_launchd_command
    with patch("auto_punch.cli.launchd.shutil.which", return_value=None):
        rc = install_launchd_command(SimpleNamespace())
    assert rc == 1
    assert list(fake_launchagents.iterdir()) == []


def test_install_aborts_when_smoke_test_fails(env_path, fake_launchagents):
    env_path.write_text(
        "APOLLO_COMPANY_CODE=a\nAPOLLO_USERNAME=u\nAPOLLO_PASSWORD=p\n"
        "APOLLO_COOKIES=c\nAUTO_PUNCH_SECRET=s\nAUTO_PUNCH_LOG=/tmp/x.log\n"
    )
    from auto_punch.cli.launchd import install_launchd_command
    with patch("auto_punch.cli.launchd.shutil.which", return_value="/path/auto-punch"), \
         patch("auto_punch.cli.launchd._smoke_test", return_value=False):
        rc = install_launchd_command(SimpleNamespace())
    assert rc == 1
    assert list(fake_launchagents.iterdir()) == []


def test_uninstall_removes_plists_and_runs_unload(fake_launchagents):
    (fake_launchagents / "com.carlos.auto-punch.morning.plist").write_text("x")
    (fake_launchagents / "com.carlos.auto-punch.evening.plist").write_text("x")
    from auto_punch.cli.launchd import uninstall_launchd_command
    with patch("auto_punch.cli.launchd.subprocess.run") as run_mock:
        rc = uninstall_launchd_command(SimpleNamespace())
    assert rc == 0
    assert list(fake_launchagents.iterdir()) == []
