from pathlib import Path

from claude_usage_windows.credentials import Credentials, FileBackend
from claude_usage_windows.snapshot import UsageSnapshot


def test_snapshot_decodes_legacy_and_limits_payloads():
    legacy = UsageSnapshot.from_payload({"five_hour": {"utilization": 45.5}})
    assert legacy.session is not None
    assert legacy.session.percent == 46

    modern = UsageSnapshot.from_payload({"limits": [
        {"kind": "session", "percent": 22},
        {"kind": "weekly_all", "percent": 63},
        {"kind": "weekly_scoped", "percent": 11, "scope": {"model": {"display_name": "Opus"}}},
    ]})
    assert [window.percent for window in modern.windows] == [22, 63, 11]
    assert modern.scoped[0].title == "Weekly · Opus"


def test_credentials_round_trip_and_file_backend(tmp_path: Path):
    credentials = Credentials("access", "refresh", 1_900_000_000, ["user:profile"])
    restored = Credentials.from_json(credentials.to_json())
    assert restored == credentials

    backend = FileBackend(tmp_path / "credentials.json")
    assert backend.write(credentials.to_json())
    assert Credentials.from_json(backend.read()).access_token == "access"
    backend.delete()
    assert backend.read() is None
