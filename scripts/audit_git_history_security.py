"""Scan every reachable Git blob without printing candidate secret values."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_repository_security import scan_bytes  # noqa: E402

DEFAULT_OUTPUT = ROOT / "docs" / "evidence" / "phase-13-public-repository-history-secret-scan.json"


@dataclass(frozen=True)
class HistoryFinding:
    blob: str
    path: str
    line: int
    rule: str


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        input=input_bytes,
        check=True,
        capture_output=True,
    )
    return result.stdout


def _reachable_blob_paths(root: Path) -> tuple[dict[str, set[str]], int]:
    revisions = _git(root, "rev-list", "--all").splitlines()
    object_lines = _git(root, "rev-list", "--objects", "--all").decode("utf-8").splitlines()
    paths_by_object: dict[str, set[str]] = defaultdict(set)
    object_ids: list[str] = []
    for line in object_lines:
        object_id, separator, path = line.partition(" ")
        object_ids.append(object_id)
        if separator and path:
            paths_by_object[object_id].add(path)

    check_input = ("\n".join(object_ids) + "\n").encode("ascii")
    check_lines = _git(
        root,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype)",
        input_bytes=check_input,
    ).decode("ascii").splitlines()
    blob_paths = {
        object_id: paths_by_object[object_id]
        for object_id, object_type in (line.split(" ", 1) for line in check_lines)
        if object_type == "blob" and paths_by_object.get(object_id)
    }
    return blob_paths, len(revisions)


def _blob_contents(root: Path, object_ids: list[str]):
    payload = _git(
        root,
        "cat-file",
        "--batch",
        input_bytes=("\n".join(object_ids) + "\n").encode("ascii"),
    )
    stream = BytesIO(payload)
    for expected_object_id in object_ids:
        header = stream.readline().decode("ascii").strip().split()
        if len(header) != 3 or header[1] != "blob":
            raise RuntimeError(f"Unexpected git cat-file response for {expected_object_id}")
        object_id, _, size_text = header
        content = stream.read(int(size_text))
        if stream.read(1) != b"\n":
            raise RuntimeError(f"Missing git cat-file delimiter for {object_id}")
        yield object_id, content


def audit(root: Path, *, progress: bool = False) -> dict[str, object]:
    root = root.resolve()
    blob_paths, revision_count = _reachable_blob_paths(root)
    findings: set[HistoryFinding] = set()
    binary_blobs = 0
    ordered_object_ids = sorted(blob_paths)
    for index, (object_id, content) in enumerate(
        _blob_contents(root, ordered_object_ids), start=1
    ):
        if progress:
            sample_path = min(blob_paths[object_id])
            print(
                f"SCAN_BLOB {index}/{len(ordered_object_ids)} {object_id[:12]} {sample_path}",
                file=sys.stderr,
                flush=True,
            )
        blob_is_binary = False
        for path in sorted(blob_paths[object_id]):
            blob_findings, is_binary = scan_bytes(content, path)
            blob_is_binary = blob_is_binary or is_binary
            findings.update(
                HistoryFinding(object_id, item.path, item.line, item.rule)
                for item in blob_findings
            )
        binary_blobs += int(blob_is_binary)

    ordered_findings = sorted(
        findings,
        key=lambda item: (item.path, item.line, item.rule, item.blob),
    )
    return {
        "schema_version": 1,
        "captured_at": datetime.now(UTC).astimezone().isoformat(),
        "scope": "all blobs reachable from all local refs",
        "revision_count": revision_count,
        "unique_blob_count": len(blob_paths),
        "binary_or_archive_blob_count": binary_blobs,
        "finding_count": len(ordered_findings),
        "findings": [asdict(finding) for finding in ordered_findings],
        "redaction_policy": "candidate values are never emitted",
        "status": "PASS" if not ordered_findings else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    report = audit(root, progress=args.progress)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
