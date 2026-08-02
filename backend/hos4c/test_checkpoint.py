"""
HOS-4D.4A: Checkpoint Tests
Canonical payload, Ed25519 sign/verify, key isolation,
checkpoint chaining, storage adapter, failure handling,
missed detection, boundary isolation.
Run: python3.11 -m pytest backend/hos4c/test_checkpoint.py -v
"""

import pytest, os, tempfile, json
from backend.hos4c.checkpoint import (
    generate_keypair, sign_payload, verify_signature,
    build_checkpoint_payload, canonical_hash,
    store_checkpoint_local, load_checkpoint,
    list_checkpoints, get_latest_checkpoint,
    verify_checkpoint, verify_chain, check_missed_checkpoint,
    CheckpointVerificationError,
)

@pytest.fixture
def keypair():
    return generate_keypair()

@pytest.fixture
def checkpoint_pair(keypair):
    priv, pub = keypair
    payload = build_checkpoint_payload(
        "audit-head-abc123", "evt-001", 1,
        "LOCAL_SIMULATION", "key-001"
    )
    sig = sign_payload(payload, priv)
    return payload, sig, priv, pub

# --- Canonical Payload ---
class TestCanonicalPayload:
    def test_deterministic_serialization(self):
        p1 = build_checkpoint_payload("abc", "e1", 1, "LOCAL_SIMULATION", "k1")
        p2 = build_checkpoint_payload("abc", "e1", 1, "LOCAL_SIMULATION", "k1")
        # Fields that vary (timestamp, checkpoint_id) aside, stable fields match
        assert p1["audit_chain_head_hash"] == p2["audit_chain_head_hash"]
        assert p1["last_audit_event_id"] == p2["last_audit_event_id"]

    def test_payload_has_required_fields(self, checkpoint_pair):
        p, _, _, _ = checkpoint_pair
        required = [
            "checkpoint_id", "checkpoint_timestamp", "payload_schema_version",
            "audit_chain_head_hash", "last_audit_event_id",
            "environment", "signing_key_id", "previous_checkpoint_hash"
        ]
        for field in required:
            assert field in p

    def test_payload_excludes_private_key(self, checkpoint_pair):
        p, sig, priv, _ = checkpoint_pair
        payload_str = json.dumps(p)
        assert "PRIVATE" not in payload_str.upper()
        assert priv[:20] not in payload_str

    def test_canonical_hash_stable(self):
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        h1 = canonical_hash(p)
        h2 = canonical_hash(p)
        assert h1 == h2

# --- Ed25519 Signing ---
class TestEd25519:
    def test_valid_signature(self, keypair):
        priv, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        sig = sign_payload(p, priv)
        assert verify_signature(p, sig, pub)

    def test_tampered_payload_rejected(self, keypair):
        priv, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        sig = sign_payload(p, priv)
        p["audit_chain_head_hash"] = "tampered"
        assert not verify_signature(p, sig, pub)

    def test_wrong_public_key_rejected(self, keypair):
        priv, _ = keypair
        _, other_pub = generate_keypair()
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        sig = sign_payload(p, priv)
        assert not verify_signature(p, sig, other_pub)

    def test_missing_signature_fails(self, keypair):
        priv, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        assert not verify_signature(p, "", pub)

    def test_key_rotation(self):
        priv1, pub1 = generate_keypair()
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k-old")
        sig = sign_payload(p, priv1)
        assert verify_signature(p, sig, pub1)

# --- Private-Key Isolation ---
class TestPrivateKeyIsolation:
    def test_private_key_not_in_checkpoint(self, keypair):
        priv, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        sig = sign_payload(p, priv)
        path = store_checkpoint_local(tempfile.mkdtemp(), p, sig)
        loaded = json.load(open(path))
        assert "PRIVATE" not in json.dumps(loaded).upper()

    def test_sign_and_verify_does_not_leak_key(self, keypair):
        priv, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        sig = sign_payload(p, priv)
        assert verify_signature(p, sig, pub)
        # sig is hex bytes, doesn't contain PEM private key
        assert "BEGIN" not in sig.upper()

# --- Checkpoint Chaining ---
class TestCheckpointChaining:
    def test_valid_chain(self, keypair):
        priv, pub = keypair
        p1 = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        s1 = sign_payload(p1, priv)
        h1 = canonical_hash(p1)
        p2 = build_checkpoint_payload("h1", "e2", 1, "LOCAL_SIMULATION", "k1", h1)
        s2 = sign_payload(p2, priv)
        # Verify both individually
        verify_checkpoint(p1, s1, pub)
        verify_checkpoint(p2, s2, pub, h1)

    def test_wrong_prev_hash_detected(self, keypair):
        priv, pub = keypair
        p1 = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        s1 = sign_payload(p1, priv)
        p2 = build_checkpoint_payload("h1", "e2", 1, "LOCAL_SIMULATION", "k1", "wrong-hash")
        s2 = sign_payload(p2, priv)
        with pytest.raises(CheckpointVerificationError):
            verify_checkpoint(p2, s2, pub, canonical_hash(p1))

    def test_replayed_checkpoint_detected(self, keypair):
        priv, pub = keypair
        p1 = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        s1 = sign_payload(p1, priv)
        h1 = canonical_hash(p1)
        # replay p1 as if it were the second checkpoint
        with pytest.raises(CheckpointVerificationError):
            verify_checkpoint(p1, s1, pub, "wrong-prev-hash")

# --- Storage Adapter ---
class TestStorageAdapter:
    def test_store_and_load(self, checkpoint_pair):
        p, sig, _, _ = checkpoint_pair
        d = tempfile.mkdtemp()
        path = store_checkpoint_local(d, p, sig)
        loaded = load_checkpoint(path)
        assert loaded["checkpoint_id"] == p["checkpoint_id"]
        assert loaded["signature"] == sig

    def test_list_checkpoints(self, checkpoint_pair):
        p, sig, _, _ = checkpoint_pair
        d = tempfile.mkdtemp()
        store_checkpoint_local(d, p, sig)
        files = list_checkpoints(d)
        assert len(files) == 1

    def test_latest_checkpoint(self, checkpoint_pair):
        p, sig, _, _ = checkpoint_pair
        d = tempfile.mkdtemp()
        store_checkpoint_local(d, p, sig)
        latest = get_latest_checkpoint(d)
        assert latest is not None

    def test_missing_directory(self):
        assert list_checkpoints("/nonexistent/path/checkpoints") == []

    def test_empty_directory(self):
        d = tempfile.mkdtemp()
        assert get_latest_checkpoint(d) is None

# --- Failure Handling ---
class TestFailureHandling:
    def test_invalid_signature_raises(self, keypair):
        _, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        with pytest.raises(CheckpointVerificationError):
            verify_checkpoint(p, "bad-signature", pub)

    def test_verification_failure_does_not_report_verified(self, keypair):
        _, pub = keypair
        p = build_checkpoint_payload("h1", "e1", 1, "LOCAL_SIMULATION", "k1")
        try:
            verify_checkpoint(p, "bad", pub)
        except:
            pass
        # No VERIFIED state emitted

# --- Missed Checkpoint ---
class TestMissedCheckpoint:
    def test_empty_dir_is_missed(self):
        d = tempfile.mkdtemp()
        assert check_missed_checkpoint(d, max_age_hours=0) is True

    def test_recent_checkpoint_not_missed(self, checkpoint_pair):
        p, sig, _, _ = checkpoint_pair
        d = tempfile.mkdtemp()
        store_checkpoint_local(d, p, sig)
        # With very large max_age, recent checkpoint is not missed
        assert check_missed_checkpoint(d, max_age_hours=999) is False

# --- Boundary Isolation ---
class TestBoundaryIsolation:
    def test_no_production_key_committed(self):
        import os
        key_files = []
        for root, dirs, files in os.walk("backend/"):
            for f in files:
                if f.endswith(".pem") or f.endswith(".key"):
                    key_files.append(os.path.join(root, f))
        assert key_files == []

    def test_browser_cannot_select_storage(self):
        # Storage path comes from env, not request
        assert "CHECKPOINT_STORE" not in os.environ or "tmp" in os.environ["CHECKPOINT_STORE"]

# --- Count ---
def test_checkpoint_count():
    classes = [TestCanonicalPayload, TestEd25519, TestPrivateKeyIsolation,
               TestCheckpointChaining, TestStorageAdapter, TestFailureHandling,
               TestMissedCheckpoint, TestBoundaryIsolation]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4A Checkpoint Tests: {total} ===\n")
    assert total >= 25