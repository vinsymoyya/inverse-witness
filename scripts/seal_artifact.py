"""Hash the reviewed release surfaces; --verify checks them without dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inverse_witness import __version__


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ARTIFACT_MANIFEST.json"
SKIP = {".git", ".venv", ".cache", "__pycache__", "tmp", "dist", "build", ".pytest_cache"}


def files():
    found = []
    for directory, subdirs, names in os.walk(ROOT):
        subdirs[:] = [name for name in subdirs if name not in SKIP and not name.endswith(".egg-info")]
        found.extend(Path(directory) / name for name in names if Path(directory) / name != MANIFEST)
    return sorted(found)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        manifest = json.loads(MANIFEST.read_text())
        expected = manifest["files"]
        actual_names = {p.relative_to(ROOT).as_posix() for p in files()}
        if actual_names != set(expected):
            raise AssertionError("Release file inventory changed")
        for name, digest in expected.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise AssertionError("Hash mismatch: " + name)
        print(f"Verified {len(expected)} release-file SHA-256 hashes")
    else:
        # Match the release's eol=lf Git contract before hashing generated text.
        for path in files():
            if path.suffix.lower() not in {".gz", ".png", ".pdf"} and not path.is_relative_to(ROOT / "data/tclab_apmonitor"):
                content = path.read_bytes()
                normalized = content.replace(b"\r\n", b"\n")
                if normalized != content:
                    path.write_bytes(normalized)
        result = {"schema": "inverse-witness.release-sha256.v1", "version": __version__,
                  "python": platform.python_version(),
                  "files": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files()}}
        MANIFEST.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Sealed {len(result['files'])} release files")


if __name__ == "__main__":
    main()
