import hashlib
from pathlib import Path

from app.evidence import sha256_file, write_json_atomic


def test_sha256(tmp_path: Path):
    path = tmp_path / "test.bin"
    path.write_bytes(b"abc")
    assert sha256_file(path) == hashlib.sha256(b"abc").hexdigest()


def test_atomic_json(tmp_path: Path):
    path = tmp_path / "manifest.json"
    write_json_atomic(path, {"ok": True})
    assert '"ok": true' in path.read_text()
