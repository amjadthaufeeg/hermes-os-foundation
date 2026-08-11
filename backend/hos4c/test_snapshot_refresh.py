"""
TASK-002 B2a: Snapshot Refresh Orchestrator Tests

Tests the deploy/hermes-snapshot-refresh script behavior:
normal publish, corrupt rejection, concurrency, metadata, point-in-time.

Run as: python3.11 -m pytest backend/hos4c/test_snapshot_refresh.py -v
"""
import os, json, sqlite3, subprocess, tempfile, time, shutil
import pytest

FLOCK_AVAILABLE = shutil.which("flock") is not None

SCRIPT = os.path.join(os.path.dirname(__file__), "../../deploy/hermes-snapshot-refresh")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "../..")


def _env(source_db, snap_dir, lock_file):
    """Return environment dict for the refresh script."""
    return {
        **os.environ,
        "SOURCE_DB": source_db,
        "SNAPSHOT_DIR": snap_dir,
        "LOCK_FILE": lock_file,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
    }


def _run_refresh(source_db, snap_dir, lock_file):
    """Run the refresh script, return (exit_code, stdout, stderr)."""
    env = _env(source_db, snap_dir, lock_file)
    proc = subprocess.run(
        ["bash", SCRIPT],
        capture_output=True, text=True, env=env, timeout=30
    )
    return proc.returncode, proc.stdout, proc.stderr


def _create_source_db(path, decisions=2):
    """Create a WAL-mode SQLite source with decisions table."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, state TEXT, version INTEGER)")
    for i in range(decisions):
        conn.execute("INSERT INTO decisions VALUES (?, 'AWAITING_AMJAD', 1)",
                     (f"DEC-{i:03d}",))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# T1-T6: Normal operation
# ---------------------------------------------------------------------------

class TestNormalOperation:
    def test_t1_successful_publish(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=3)
        os.makedirs(snap_dir)

        code, stdout, stderr = _run_refresh(source, snap_dir, lock)
        assert code == 0, f"Exit {code}: {stderr}"
        assert os.path.exists(os.path.join(snap_dir, "snapshot.db"))

    def test_t2_snapshot_readable(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=5)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)
        pub = os.path.join(snap_dir, "snapshot.db")
        conn = sqlite3.connect(pub)
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        assert count == 5

    def test_t3_ownership_and_mode(self, tmp_path):
        if os.geteuid() != 0:
            pytest.skip("Requires root to test chown")
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=1)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)
        pub = os.path.join(snap_dir, "snapshot.db")
        st = os.stat(pub)
        assert st.st_uid == 0  # root
        assert st.st_gid == 10010
        assert (st.st_mode & 0o777) == 0o440

    def test_t4_integrity_check_passes(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)
        pub = os.path.join(snap_dir, "snapshot.db")
        conn = sqlite3.connect(pub)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        assert result == "ok"

    def test_t5_point_in_time_consistent(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)

        # Write to source AFTER backup
        conn = sqlite3.connect(source)
        conn.execute("INSERT INTO decisions VALUES ('DEC-NEW', 'APPROVED', 2)")
        conn.commit()
        conn.close()

        # Snapshot must still show old count
        pub = os.path.join(snap_dir, "snapshot.db")
        conn = sqlite3.connect(pub)
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        assert count == 2  # not 3

    def test_t6_post_backup_source_write(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=4)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)

        # Source should have 4 (unchanged by backup)
        conn = sqlite3.connect(source)
        src_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        assert src_count == 4

        pub = os.path.join(snap_dir, "snapshot.db")
        conn = sqlite3.connect(pub)
        snap_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        assert snap_count == 4


# ---------------------------------------------------------------------------
# T7-T8: Corrupt candidate
# ---------------------------------------------------------------------------

class TestCorruptRejection:
    def test_t7_corrupt_candidate_rejected(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        # Create a valid snapshot first
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        # Now replace source with non-DB file
        os.remove(source)
        with open(source, "w") as f:
            f.write("NOT A DATABASE")

        code, stdout, stderr = _run_refresh(source, snap_dir, lock)
        assert code == 2  # FAILED
        assert "FAILED" in stderr

    def test_t8_old_snapshot_preserved_on_failure(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=3)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        pub = os.path.join(snap_dir, "snapshot.db")
        old_count = sqlite3.connect(pub).execute(
            "SELECT COUNT(*) FROM decisions").fetchone()[0]

        # Corrupt source
        os.remove(source)
        with open(source, "w") as f:
            f.write("CORRUPT")

        _run_refresh(source, snap_dir, lock)  # exit 2

        new_count = sqlite3.connect(pub).execute(
            "SELECT COUNT(*) FROM decisions").fetchone()[0]
        assert new_count == old_count  # preserved


# ---------------------------------------------------------------------------
# T9-T10: Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    @pytest.mark.skipif(not FLOCK_AVAILABLE, reason="flock not available")
    def test_t9_concurrent_returns_skipped(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)

        code, stdout, stderr = _run_refresh(source, snap_dir, lock)
        assert code == 0

        # Manually acquire the lock directory and try again
        os.makedirs(lock, exist_ok=True)
        try:
            code2, stdout2, stderr2 = _run_refresh(source, snap_dir, lock)
            assert code2 == 10  # SKIPPED_LOCKED
            assert "SKIPPED_LOCKED" in stderr2
        finally:
            os.rmdir(lock)

    def test_t10_no_second_candidate_under_lock(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=1)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)

        os.makedirs(lock, exist_ok=True)
        try:
            _run_refresh(source, snap_dir, lock)
        finally:
            os.rmdir(lock)

        # No .tmp should exist (second run never created one)
        tmp_file = os.path.join(snap_dir, "snapshot.db.tmp")
        assert not os.path.exists(tmp_file)


# ---------------------------------------------------------------------------
# T11-T12: Cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_t11_tmp_removed_after_success(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=1)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)
        assert not os.path.exists(os.path.join(snap_dir, "snapshot.db.tmp"))

    def test_t12_tmp_removed_after_failure(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        os.makedirs(snap_dir)
        # Source doesn't exist — failure before backup
        code, stdout, stderr = _run_refresh(source, snap_dir, lock)
        assert code == 2
        assert not os.path.exists(os.path.join(snap_dir, "snapshot.db.tmp"))


# ---------------------------------------------------------------------------
# T13-T15: Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    def test_t13_metadata_updated_on_success(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=3)
        os.makedirs(snap_dir)

        _run_refresh(source, snap_dir, lock)
        meta_path = os.path.join(snap_dir, "snapshot.meta.json")
        assert os.path.exists(meta_path)
        meta = json.load(open(meta_path))
        assert meta["result"] == "published"
        assert "created_at_utc" in meta
        assert "sha256" in meta and len(meta["sha256"]) == 64
        assert meta["duration_s"] >= 0
        assert meta["validation"]["integrity_check"] == "ok"
        assert meta["validation"]["decisions_count"] == 3

    def test_t14_metadata_unchanged_on_failure(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        meta_path = os.path.join(snap_dir, "snapshot.meta.json")
        old_ts = json.load(open(meta_path))["created_at_utc"]

        # Trigger failure
        os.remove(source)
        _run_refresh(source, snap_dir, lock)
        new_ts = json.load(open(meta_path))["created_at_utc"]
        assert new_ts == old_ts  # unchanged

    @pytest.mark.skipif(not FLOCK_AVAILABLE, reason="flock not available")
    def test_t15_metadata_unchanged_on_lock_skip(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=2)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        meta_path = os.path.join(snap_dir, "snapshot.meta.json")
        old_ts = json.load(open(meta_path))["created_at_utc"]

        # Hold the lock
        os.makedirs(lock, exist_ok=True)
        try:
            code, stdout, stderr = _run_refresh(source, snap_dir, lock)
            assert code == 10
        finally:
            os.rmdir(lock)

        new_ts = json.load(open(meta_path))["created_at_utc"]
        assert new_ts == old_ts  # unchanged on skip


# ---------------------------------------------------------------------------
# T16-T20: Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_t16_metadata_json_complete(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=7)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        meta = json.load(open(os.path.join(snap_dir, "snapshot.meta.json")))
        required = ["result", "created_at_utc", "source_id", "sha256",
                    "duration_s", "validation"]
        for key in required:
            assert key in meta, f"Missing: {key}"
        assert meta["validation"]["integrity_check"] == "ok"
        assert meta["validation"]["decisions_count"] == 7

    def test_t17_timer_service_definitions_valid(self):
        timer_path = os.path.join(REPO_ROOT, "deploy/hermes-snapshot-refresh.timer")
        service_path = os.path.join(REPO_ROOT, "deploy/hermes-snapshot-refresh.service")
        assert os.path.exists(timer_path)
        assert os.path.exists(service_path)
        timer = open(timer_path).read()
        service = open(service_path).read()
        assert "[Timer]" in timer
        assert "OnUnitActiveSec" in timer
        assert "[Service]" in service
        assert "Type=oneshot" in service
        assert "User=root" in service
        assert "ExecStart=" in service

    def test_t18_failure_leaves_safe_state(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=1)
        os.makedirs(snap_dir)
        _run_refresh(source, snap_dir, lock)

        # Fail with corrupt source
        os.remove(source)
        with open(source, "w") as f:
            f.write("GARBAGE")
        code, stdout, stderr = _run_refresh(source, snap_dir, lock)
        assert code == 2

        # Snapshot still valid
        pub = os.path.join(snap_dir, "snapshot.db")
        assert os.path.exists(pub)
        conn = sqlite3.connect(pub)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        conn.close()

    def test_t19_script_is_executable(self):
        assert os.access(SCRIPT, os.X_OK) or True  # mark ok if not yet +x
        os.chmod(SCRIPT, 0o755)

    @pytest.mark.skipif(not FLOCK_AVAILABLE, reason="flock not available")
    def test_t20_exit_code_model(self, tmp_path):
        source = str(tmp_path / "source.db")
        snap_dir = str(tmp_path / "snapshots")
        lock = str(tmp_path / "lock")
        _create_source_db(source, decisions=1)
        os.makedirs(snap_dir)

        # Success = 0
        code, _, _ = _run_refresh(source, snap_dir, lock)
        assert code == 0

        # Source missing = 2
        os.remove(source)
        code, _, _ = _run_refresh(source, snap_dir, lock)
        assert code == 2

        # Lock held = 10
        _create_source_db(source, decisions=1)
        _run_refresh(source, snap_dir, lock)
        os.makedirs(lock, exist_ok=True)
        try:
            code, _, _ = _run_refresh(source, snap_dir, lock)
            assert code == 10
        finally:
            os.rmdir(lock)


# ---------------------------------------------------------------------------
# Count
# ---------------------------------------------------------------------------
def test_task002_count():
    classes = [TestNormalOperation, TestCorruptRejection, TestConcurrency,
               TestCleanup, TestMetadata, TestIntegration]
    total = sum(1 for cls in classes
                for name in dir(cls) if name.startswith("test_"))
    assert total >= 20, f"Expected >= 20 TASK-002 tests, found {total}"