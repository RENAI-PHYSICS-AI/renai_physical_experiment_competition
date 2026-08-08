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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("formal", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("current_header", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    formal = load_records(args.formal)
    candidate = load_records(args.candidate)
    formal_julia = {path: record for path, record in formal.items() if path.startswith("julia_app/")}
    candidate_julia = {path: record for path, record in candidate.items() if path.startswith("julia_app/")}

    julia_missing = sorted(set(formal_julia) - set(candidate_julia))
    julia_extra = sorted(set(candidate_julia) - set(formal_julia))
    julia_changed = sorted(
        path
        for path in set(formal_julia) & set(candidate_julia)
        if formal_julia[path] != candidate_julia[path]
    )

    header_hash = hashlib.sha256(args.current_header.read_bytes()).hexdigest().upper()
    report = {
        "formal_julia_count": len(formal_julia),
        "candidate_julia_count": len(candidate_julia),
        "formal_julia_tree_sha256": tree_digest(formal, "julia_app/"),
        "candidate_julia_tree_sha256": tree_digest(candidate, "julia_app/"),
        "julia_missing": julia_missing,
        "julia_extra": julia_extra,
        "julia_changed": julia_changed,
        "app_py_unchanged": formal.get("app/app.py") == candidate.get("app/app.py"),
        "prompts_unchanged": {
            path: formal.get(path) == candidate.get(path)
            for path in sorted(set(formal) | set(candidate))
            if path.startswith("app/prompts/")
        },
        "formal_header_sha256": formal["app/assets/sound_speed_header.png"]["sha256"],
        "candidate_header_sha256": candidate["app/assets/sound_speed_header.png"]["sha256"],
        "current_header_sha256": header_hash,
        "candidate_header_matches_current": candidate["app/assets/sound_speed_header.png"]["sha256"] == header_hash,
    }
    report["passed"] = bool(
        not julia_missing
        and not julia_extra
        and not julia_changed
        and report["app_py_unchanged"]
        and all(report["prompts_unchanged"].values())
        and report["candidate_header_matches_current"]
        and report["formal_header_sha256"] != report["candidate_header_sha256"]
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
