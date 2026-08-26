from deploy.builder_dispatch.adapter import redact
from deploy.builder_dispatch.mac_worker import _path_allowed, _path_protected


def test_secret_redaction_bearer_and_github_token():
    text = "Authorization: Bearer abc.def.ghi ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    out = redact(text)
    assert "abc.def.ghi" not in out
    assert "ghp_" not in out
    assert "[REDACTED]" in out


def test_allowed_files_glob():
    allowed = ["deploy/builder_dispatch/**", "docs/tasks/*.md"]
    assert _path_allowed("deploy/builder_dispatch/adapter.py", allowed)
    assert _path_allowed("docs/tasks/TASK-1.md", allowed)
    assert not _path_allowed("backend/app.py", allowed)


def test_protected_paths_prefix_and_glob():
    protected = [".github/", "deploy/prod/**", "secrets.env"]
    assert _path_protected(".github/workflows/ci.yml", protected)
    assert _path_protected("deploy/prod/config.yml", protected)
    assert _path_protected("secrets.env", protected)
    assert not _path_protected("deploy/builder_dispatch/adapter.py", protected)
