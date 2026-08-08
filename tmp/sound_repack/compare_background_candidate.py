from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load_records(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["path"]): record for record in payload["records"]}


def tree_digest(records: dict[str, dict[str, object]], prefix: str) -> str:
    digest = hashlib.sha256()
    for path, record in sorted(records.items()):
        if path.startswith(prefix):
            digest.update(
                f"{path}\0{record['size']}\0{record['sha256']}\0{record['typecode']}\n".encode("utf-8")
            )
    return digest.hexdigest().upper()


def compare_prefix(
    formal: dict[str, dict[str, object]], candidate: dict[str, dict[str, object]], prefix: str
) -> dict[str, object]:
    left = {path: record for path, record in formal.items() if path.startswith(prefix)}
    right = {path: record for path, record in candidate.items() if path.startswith(prefix)}
    missing = sorted(set(left) - set(right))
    extra = sorted(set(right) - set(left))
    changed = sorted(path for path in set(left) & set(right) if left[path] != right[path])
    return {
        "formal_count": len(left),
        "candidate_count": len(right),
        "formal_tree_sha256": tree_digest(formal, prefix),
        "candidate_tree_sha256": tree_digest(candidate, prefix),
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "passed": not missing and not extra and not changed,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("formal_manifest", type=Path)
    parser.add_argument("candidate_manifest", type=Path)
    parser.add_argument("formal_extract", type=Path)
    parser.add_argument("candidate_extract", type=Path)
    parser.add_argument("source_app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    formal = load_records(args.formal_manifest)
    candidate = load_records(args.candidate_manifest)
    julia = compare_prefix(formal, candidate, "julia_app/")
    data = compare_prefix(formal, candidate, "app/data/")
    prompts = compare_prefix(formal, candidate, "app/prompts/")

    formal_app_path = args.formal_extract / "app" / "app.py"
    candidate_app_path = args.candidate_extract / "app" / "app.py"
    formal_text = formal_app_path.read_text(encoding="utf-8")
    candidate_text = candidate_app_path.read_text(encoding="utf-8")
    expected_text = formal_text.replace("background: #17334f;", "background: #15365b;")
    app_check = {
        "formal_sha256": sha256_file(formal_app_path),
        "candidate_sha256": sha256_file(candidate_app_path),
        "source_sha256": sha256_file(args.source_app),
        "formal_old_color_count": formal_text.count("#17334f"),
        "formal_new_color_count": formal_text.count("#15365b"),
        "candidate_old_color_count": candidate_text.count("#17334f"),
        "candidate_new_color_count": candidate_text.count("#15365b"),
        "exact_single_replacement": expected_text == candidate_text,
        "candidate_matches_source": candidate_app_path.read_bytes() == args.source_app.read_bytes(),
    }
    app_check["passed"] = bool(
        app_check["formal_old_color_count"] == 1
        and app_check["formal_new_color_count"] == 0
        and app_check["candidate_old_color_count"] == 0
        and app_check["candidate_new_color_count"] == 1
        and app_check["exact_single_replacement"]
        and app_check["candidate_matches_source"]
    )

    formal_header = formal["app/assets/sound_speed_header.png"]
    candidate_header = candidate["app/assets/sound_speed_header.png"]
    header = {
        "formal_sha256": formal_header["sha256"],
        "candidate_sha256": candidate_header["sha256"],
        "unchanged": formal_header == candidate_header,
    }

    report = {
        "julia": julia,
        "data": data,
        "prompts": prompts,
        "header": header,
        "app_py": app_check,
    }
    report["passed"] = bool(
        julia["passed"]
        and data["passed"]
        and prompts["passed"]
        and header["unchanged"]
        and app_check["passed"]
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
