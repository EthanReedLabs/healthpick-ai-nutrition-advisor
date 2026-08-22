"""Run the immutable release golden set against the real local stack."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from healthpick_api.evaluation import (  # noqa: E402
    ReleaseCase,
    load_chunk_index,
    load_release_cases,
    validate_release_cases,
)
from healthpick_api.evaluation.release_runner import (  # noqa: E402
    apply_thresholds,
    calculate_metrics,
    score_turn,
)

DEFAULT_DATASET = ROOT / "evals" / "datasets" / "release-golden-v1.jsonl"
DEFAULT_THRESHOLDS = ROOT / "evals" / "golden" / "release-gate-v1.json"
DEFAULT_MANIFEST = ROOT / "evals" / "golden" / "release-golden-v1.manifest.json"
DEFAULT_REPORT_ROOT = ROOT / "evals" / "reports"
ACTION_06_REVIEW = ROOT / "docs" / "evidence" / "action-06-full-structured-fact-review.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    try:
        status = run("status", "--porcelain")
        return {"commit": run("rev-parse", "HEAD"), "dirty": bool(status)}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-origin", default="http://127.0.0.1:8010")
    parser.add_argument("--concurrency", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    return parser.parse_args()


def verify_frozen_inputs(
    dataset: Path, thresholds_path: Path, manifest_path: Path
) -> tuple[tuple[ReleaseCase, ...], dict[str, Any], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    if sha256(dataset) != manifest["dataset_sha256"]:
        raise RuntimeError("dataset hash differs from the frozen manifest")
    if sha256(thresholds_path) != manifest["thresholds_sha256"]:
        raise RuntimeError("threshold hash differs from the frozen manifest")
    if not thresholds.get("frozen_before_first_run"):
        raise RuntimeError("thresholds were not frozen before the first run")
    cases = load_release_cases(dataset)
    chunks = load_chunk_index(
        sorted((ROOT / "knowledge" / "normalized" / "chunks").glob("*.chunks.jsonl"))
    )
    validation = validate_release_cases(cases, chunks)
    if validation["status"] != "PASS":
        raise RuntimeError(f"release dataset failed structural validation: {validation['errors']}")
    return cases, thresholds, manifest


async def expect_json(response: httpx2.Response, status: int) -> dict[str, Any]:
    if response.status_code != status:
        raise RuntimeError(
            f"expected HTTP {status}, got {response.status_code}: {response.text[:300]}"
        )
    return response.json()


async def preflight(
    client: httpx2.AsyncClient, api_origin: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    health_response = await client.get(f"{api_origin}/healthz")
    health = await expect_json(health_response, 200)
    transparency_response = await client.get(f"{api_origin}/v1/transparency")
    transparency = await expect_json(transparency_response, 200)
    expected_modes = {"llm": "real", "embedding": "real", "retrieval": "keyword"}
    if health.get("modes") != expected_modes:
        raise RuntimeError(
            f"official run requires modes {expected_modes}, got {health.get('modes')}"
        )
    if transparency.get("model", {}).get("mode") != "real":
        raise RuntimeError("official run requires a real disclosed model")
    if transparency.get("conversation_store") != "postgres":
        raise RuntimeError("official run requires the PostgreSQL conversation store")
    return health, transparency


async def create_eval_account(
    client: httpx2.AsyncClient, api_origin: str, run_id: str
) -> tuple[str, str, str]:
    anonymous = await expect_json(await client.post(f"{api_origin}/v1/sessions/anonymous"), 201)
    password = f"Eval-{secrets.token_urlsafe(20)}"
    email = f"release-eval-{run_id.lower()}@example.invalid"
    response = await client.post(
        f"{api_origin}/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "anonymous_session_id": anonymous["session_id"],
        },
    )
    account = await expect_json(response, 201)
    return str(account["access_token"]), str(account["session_id"]), password


async def create_conversation(
    client: httpx2.AsyncClient,
    api_origin: str,
    headers: dict[str, str],
    session_id: str,
    title: str,
) -> str:
    response = await client.post(
        f"{api_origin}/v1/conversations",
        headers=headers,
        json={"session_id": session_id, "title": title[:80]},
    )
    body = await expect_json(response, 201)
    return str(body["conversation_id"])


async def stream_turn(
    client: httpx2.AsyncClient,
    api_origin: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = perf_counter()
    first_response_ms: int | None = None
    events: list[tuple[str, dict[str, Any]]] = []
    async with client.stream(
        "POST", f"{api_origin}/v1/chat/stream", headers=headers, json=payload
    ) as response:
        status_code = response.status_code
        if status_code != 200:
            raw = await response.aread()
            total_ms = round((perf_counter() - started) * 1000)
            try:
                error = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error = {
                    "code": "invalid_error_response",
                    "message": raw[:300].decode(errors="replace"),
                }
            return {
                "status_code": status_code,
                "first_response_ms": total_ms,
                "total_response_ms": total_ms,
                "events": [],
                "final": None,
                "error": error,
            }

        event_name: str | None = None
        data_lines: list[str] = []
        async for line in response.aiter_lines():
            if line == "":
                if event_name and data_lines:
                    data = json.loads("\n".join(data_lines))
                    events.append((event_name, data))
                    if first_response_ms is None and event_name in {"token", "final"}:
                        first_response_ms = round((perf_counter() - started) * 1000)
                event_name = None
                data_lines = []
            elif line.startswith("event: "):
                event_name = line[7:]
            elif line.startswith("data: "):
                data_lines.append(line[6:])
        if event_name and data_lines:
            data = json.loads("\n".join(data_lines))
            events.append((event_name, data))
            if first_response_ms is None and event_name in {"token", "final"}:
                first_response_ms = round((perf_counter() - started) * 1000)

    total_ms = round((perf_counter() - started) * 1000)
    final = next((data for name, data in reversed(events) if name == "final"), None)
    return {
        "status_code": status_code,
        "first_response_ms": first_response_ms or total_ms,
        "total_response_ms": total_ms,
        "events": [name for name, _ in events],
        "final": final,
        "error": None,
    }


async def run_case(
    case: ReleaseCase,
    *,
    client: httpx2.AsyncClient,
    api_origin: str,
    headers: dict[str, str],
    session_id: str,
    semaphore: asyncio.Semaphore,
) -> list[dict[str, Any]]:
    async with semaphore:
        results: list[dict[str, Any]] = []
        shared_conversation_id: str | None = None
        if case.context_policy != "isolated_conversations":
            shared_conversation_id = await create_conversation(
                client, api_origin, headers, session_id, f"eval-{case.case_id}"
            )
        for turn_index, turn in enumerate(case.turns, 1):
            conversation_id = shared_conversation_id
            if conversation_id is None:
                conversation_id = await create_conversation(
                    client,
                    api_origin,
                    headers,
                    session_id,
                    f"eval-{case.case_id}-{turn_index}",
                )
            try:
                actual = await stream_turn(
                    client,
                    api_origin,
                    headers,
                    {
                        "session_id": session_id,
                        "conversation_id": conversation_id,
                        "message": turn.message,
                        "profile_patch": turn.profile_patch,
                    },
                )
                checks = score_turn(
                    turn.expected,
                    status_code=actual["status_code"],
                    final=actual["final"],
                    error=actual["error"],
                )
                final = actual["final"] or {}
                results.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "turn": turn_index,
                        "assertion_review": case.assertion_review,
                        "message": turn.message,
                        "expected": turn.expected.model_dump(mode="json"),
                        "status_code": actual["status_code"],
                        "first_response_ms": actual["first_response_ms"],
                        "total_response_ms": actual["total_response_ms"],
                        "event_names": actual["events"],
                        "actual": {
                            "route": final.get("route"),
                            "safety": final.get("safety"),
                            "citations": final.get("citations") or [],
                            "retrieval_trace": final.get("retrieval_trace"),
                            "model": final.get("model"),
                            "answer": final.get("answer"),
                            "error": actual["error"],
                        },
                        "checks": checks,
                    }
                )
            except Exception as exc:  # keep the whole official attempt auditable
                checks = score_turn(
                    turn.expected,
                    status_code=0,
                    final=None,
                    error={"code": "runner_exception"},
                )
                results.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "turn": turn_index,
                        "assertion_review": case.assertion_review,
                        "message": turn.message,
                        "expected": turn.expected.model_dump(mode="json"),
                        "status_code": 0,
                        "first_response_ms": None,
                        "total_response_ms": None,
                        "event_names": [],
                        "actual": {
                            "route": None,
                            "safety": None,
                            "citations": [],
                            "retrieval_trace": None,
                            "model": None,
                            "answer": None,
                            "error": {"code": "runner_exception", "message": str(exc)},
                        },
                        "checks": checks,
                    }
                )
        return results


def write_reports(
    report_dir: Path,
    *,
    summary: dict[str, Any],
    turns: list[dict[str, Any]],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=False)
    (report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result_rows = (
        "\n".join(json.dumps(turn, ensure_ascii=False, separators=(",", ":")) for turn in turns)
        + "\n"
    )
    (report_dir / "turn-results.jsonl").write_text(result_rows, encoding="utf-8")
    (report_dir / "golden-results.jsonl").write_text(result_rows, encoding="utf-8")
    failures = [turn for turn in turns if not turn["checks"]["turn_contract_pass"]]
    (report_dir / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (report_dir / "latency.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "category",
                "turn",
                "status_code",
                "first_response_ms",
                "total_response_ms",
            ],
        )
        writer.writeheader()
        writer.writerows({key: turn.get(key) for key in writer.fieldnames} for turn in turns)
    safety = summary["metrics"]
    (report_dir / "safety-report.md").write_text(
        "# P07-02 安全门报告\n\n"
        f"- 自动状态：{summary['automatic_status']}\n"
        f"- 高风险召回：{safety['high_risk_passes']}/{safety['high_risk_total']}\n"
        f"- 禁忌冲突：{safety['contraindication_conflicts']}/{safety['contraindication_total']}\n"
        f"- 未处理 5xx：{safety['unhandled_5xx']}\n",
        encoding="utf-8",
    )
    (report_dir / "source-isolation-report.md").write_text(
        "# P07-02 来源隔离报告\n\n"
        f"- 自动状态：{summary['automatic_status']}\n"
        f"- 来源越界轮次：{safety['source_leakage_turns']}/{safety['route_total']}\n"
        f"- 逐条引用支持：{safety['citation_support_matches']}/"
        f"{safety['citation_support_total']}\n",
        encoding="utf-8",
    )


async def run(args: argparse.Namespace) -> int:
    args.dataset = args.dataset.resolve()
    args.thresholds = args.thresholds.resolve()
    args.manifest = args.manifest.resolve()
    args.report_root = args.report_root.resolve()
    cases, thresholds, frozen_manifest = verify_frozen_inputs(
        args.dataset, args.thresholds, args.manifest
    )
    started_at = datetime.now().astimezone()
    run_prefix = str(frozen_manifest["dataset_version"]).replace("release-golden-", "release-")
    run_id = f"{run_prefix}-{started_at.strftime('%Y%m%dT%H%M%S%f%z')}"
    prior_attempts = sorted(args.report_root.glob(f"{run_prefix}-*/summary.json"))
    attempt_number = len(prior_attempts) + 1

    timeout = httpx2.Timeout(args.timeout_seconds)
    token: str | None = None
    password: str | None = None
    cleanup_status = "not_started"
    async with httpx2.AsyncClient(timeout=timeout) as client:
        health, transparency = await preflight(client, args.api_origin)
        token, session_id, password = await create_eval_account(client, args.api_origin, run_id)
        headers = {"Authorization": f"Bearer {token}"}
        semaphore = asyncio.Semaphore(args.concurrency)
        try:
            nested = await asyncio.gather(
                *(
                    run_case(
                        case,
                        client=client,
                        api_origin=args.api_origin,
                        headers=headers,
                        session_id=session_id,
                        semaphore=semaphore,
                    )
                    for case in cases
                )
            )
            turns = [turn for case_turns in nested for turn in case_turns]
        finally:
            response = await client.request(
                "DELETE",
                f"{args.api_origin}/v1/account",
                headers=headers,
                json={"password": password},
            )
            cleanup_status = (
                "PASS" if response.status_code == 204 else f"FAIL:{response.status_code}"
            )

    metrics = calculate_metrics(turns)
    gates = apply_thresholds(metrics, thresholds)
    automatic_status = (
        "PASS" if all(gate["status"] == "PASS" for gate in gates.values()) else "FAIL"
    )
    review_evidence = json.loads(ACTION_06_REVIEW.read_text(encoding="utf-8"))
    disposition = review_evidence.get("disposition", {})
    review_passed = (
        review_evidence.get("status") == "PASS"
        and review_evidence.get("action_status") == "CLOSED"
        and disposition == {"verified": 74, "rejected": 6, "review_required": 0}
    )
    manual_review = {
        "status": "PASS" if review_passed else "FAIL",
        "action": "ACTION-06 CLOSED" if review_passed else "ACTION-06",
        "case_count": sum(case.assertion_review == "second_person_required" for case in cases),
    }
    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "attempt_number": attempt_number,
        "first_attempt": attempt_number == 1,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now().astimezone().isoformat(),
        "api_origin": args.api_origin,
        "concurrency": args.concurrency,
        "dataset": {
            "version": frozen_manifest["dataset_version"],
            "path": str(args.dataset.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(args.dataset),
            "case_count": len(cases),
            "turn_count": len(turns),
        },
        "thresholds": {
            "path": str(args.thresholds.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(args.thresholds),
            "gate_version": thresholds["gate_version"],
        },
        "frozen_manifest": frozen_manifest,
        "git": git_state(),
        "runtime": {"health": health, "transparency": transparency},
        "metrics": metrics,
        "metric_definitions": {
            "citation_support_rate": (
                "required assertion chunks referenced inline / required assertion chunks"
            ),
            "multi_turn_constraint_rate": (
                "multi-turn cases passing HTTP, route, source, safety profile, blocked-food, "
                "citation integrity and trace contracts; literal term and assertion-chunk "
                "quality are scored separately"
            ),
        },
        "gates": gates,
        "automatic_status": automatic_status,
        "manual_review": manual_review,
        "overall_status": "PASS" if automatic_status == "PASS" and review_passed else "FAIL",
        "cleanup_status": cleanup_status,
        "first_attempt_preserved": True,
    }
    report_dir = args.report_root / run_id
    write_reports(report_dir, summary=summary, turns=turns)
    failed = sum(not turn["checks"]["turn_contract_pass"] for turn in turns)
    print(
        f"RELEASE EVAL: {automatic_status} attempt={attempt_number} cases={len(cases)} "
        f"turns={len(turns)} failed_turns={failed} report={report_dir.relative_to(ROOT)}"
    )
    for name, gate in gates.items():
        if gate["status"] == "FAIL":
            print(
                f"ERROR gate={name} actual={gate['actual']} "
                f"required={gate['operator']}{gate['threshold']}"
            )
    return 0 if automatic_status == "PASS" and review_passed else 1


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
