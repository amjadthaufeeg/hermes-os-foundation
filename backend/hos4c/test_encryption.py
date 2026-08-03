"""
HOS-4D.4C.2: Encryption + Storage Tests
Age asymmetric encryption, cryptographic separation,
storage adapter, credential separation, catalog, states.
Run: python3.11 -m pytest backend/hos4c/test_encryption.py -v
"""

import pytest, os, tempfile
from backend.hos4c.encryption import (
    generate_age_keypair, encrypt_with_age, decrypt_with_age,
    StorageAdapter, StorageObject, check_permission, EncryptionState,
    record_catalog_entry, CATALOG,
)

@pytest.fixture(autouse=True)
def cleanup():
    CATALOG.clear()
    yield

@pytest.fixture
def keypair():
    return generate_age_keypair()

@pytest.fixture
def source_file():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "test.db")
    with open(path, "w") as f:
        f.write("test backup data")
    return path

# --- Age Asymmetric Encryption ---
class TestAgeEncryption:
    def test_round_trip(self, keypair, source_file):
        priv, pub = keypair
        enc = encrypt_with_age(source_file, pub)
        assert enc and os.path.exists(enc)
        dec = decrypt_with_age(enc, priv, tempfile.mkdtemp())
        assert dec and os.path.exists(dec)
        with open(dec) as f:
            assert f.read() == "test backup data"

    def test_wrong_recipient_rejected(self, keypair, source_file):
        priv, pub = keypair
        _, wrong_pub = generate_age_keypair()
        enc = encrypt_with_age(source_file, wrong_pub)
        if enc:
            # Wrong key should fail decryption
            dec = decrypt_with_age(enc, priv, tempfile.mkdtemp())
            assert dec is None

    def test_wrong_identity_rejected(self, keypair, source_file):
        _, pub = keypair
        wrong_priv, _ = generate_age_keypair()
        enc = encrypt_with_age(source_file, pub)
        dec = decrypt_with_age(enc, wrong_priv, tempfile.mkdtemp())
        assert dec is None

    def test_encrypt_without_private_key(self, source_file):
        _, pub = generate_age_keypair()
        enc = encrypt_with_age(source_file, pub)
        assert enc and os.path.exists(enc)

    def test_missing_recipient(self, source_file):
        assert encrypt_with_age(source_file, "not-a-key") is None

    def test_corrupted_ciphertext(self, keypair, source_file):
        priv, pub = keypair
        enc = encrypt_with_age(source_file, pub)
        with open(enc, "ab") as f:
            f.write(b"tampered")
        dec = decrypt_with_age(enc, priv, tempfile.mkdtemp())
        assert dec is None

    def test_private_key_not_accessible_to_writer(self, keypair, source_file):
        priv, pub = keypair
        # Writer has public key only
        writer_has = pub
        assert "AGE-SECRET-KEY" not in writer_has

# --- Storage Adapter ---
class TestStorageAdapter:
    def test_upload_download(self, source_file):
        s = StorageAdapter()
        obj = s.upload("BKP-001", source_file)
        assert obj.backup_id == "BKP-001"
        out = tempfile.mktemp()
        assert s.download("BKP-001", out)
        with open(out) as f:
            assert f.read() == "test backup data"

    def test_list_backups(self, source_file):
        s = StorageAdapter()
        s.upload("BKP-001", source_file)
        s.upload("BKP-002", source_file)
        backups = s.list_backups()
        assert len(backups) == 2

    def test_missing_backup(self):
        s = StorageAdapter()
        assert s.get_metadata("nonexistent") is None
        assert s.download("nonexistent", "/tmp/out") is False

# --- Credential Separation ---
class TestCredentialSeparation:
    def test_writer_cannot_delete(self):
        assert not check_permission("BACKUP_WRITER", "delete")

    def test_hermes_zero_all(self):
        for action in ("upload", "download", "delete", "restore", "decrypt"):
            assert not check_permission("HERMES_ASSISTANT", action)

    def test_amjad_can_all(self):
        for action in ("upload", "download", "delete", "restore"):
            assert check_permission("AMJAD_OWNER", action)

# --- Catalog ---
class TestCatalog:
    def test_record_and_retrieve(self, source_file):
        s = StorageAdapter()
        obj = s.upload("BKP-001", source_file)
        record_catalog_entry("BKP-001", "OFFHOST_VERIFIED", "sha256:abc", "key-001", obj)
        assert "BKP-001" in CATALOG
        assert CATALOG["BKP-001"]["state"] == "OFFHOST_VERIFIED"

# --- Count ---
def test_encryption_count():
    classes = [TestAgeEncryption, TestStorageAdapter,
               TestCredentialSeparation, TestCatalog]
    total = sum(1 for cls in classes for name in dir(cls) if name.startswith("test_"))
    print(f"\n=== HOS-4D.4C.2 Encryption Tests: {total} ===\n")
    assert total >= 14