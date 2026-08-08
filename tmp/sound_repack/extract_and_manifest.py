from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath

from PyInstaller.archive.readers import CArchiveReader


PREFIXES = (
    "julia_app\\",
    "app\\app.py",
    "app\\prompts\\",
    "app\\data\\",
    "app\\assets\\sound_speed_header.png",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def safe_destination(root: Path, archive_name: str) -> Path:
    parts = PureWindowsPath(archive_name).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Unsafe archive path: {archive_name!r}")
    destination = root.joinpath(*parts).resolve()
    root_resolved = root.resolve()
    if destination != root_resolved and root_resolved not in destination.parents:
        raise ValueError(f"Archive path escapes extraction root: {archive_name!r}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    exe = args.exe.resolve(strict=True)
    output = args.output.resolve()
    manifest_path = args.manifest.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    archive = CArchiveReader(str(exe))
    selected = [
        name
        for name in archive.toc
        if name == "app\\app.py"
        or name == "app\\assets\\sound_speed_header.png"
        or name.startswith("app\\prompts\\")
        or name.startswith("app\\data\\")
        or name.startswith("julia_app\\")
    ]
    if not selected:
        raise RuntimeError("No requested entries found in the executable archive.")

    records: list[dict[str, object]] = []
    for index, name in enumerate(sorted(selected), start=1):
        data = archive.extract(name)
        destination = safe_destination(output, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        entry = archive.toc[name]
        records.append(
            {
                "path": name.replace("\\", "/"),
                "size": len(data),
                "sha256": sha256_bytes(data),
                "typecode": entry[-1],
            }
        )
        if index % 500 == 0:
            print(f"extracted={index}/{len(selected)}", flush=True)

    manifest = {
        "source_exe": str(exe),
        "source_exe_size": exe.stat().st_size,
        "source_exe_sha256": sha256_file(exe),
        "file_count": len(records),
        "julia_file_count": sum(1 for record in records if str(record["path"]).startswith("julia_app/")),
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in manifest if key != "records"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
