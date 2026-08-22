"""Validate and render the project-wide execution control plane."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "control" / "project-control.yaml"
CONTROL_SCHEMA = ROOT / "control" / "schemas" / "project-control.schema.json"
RECORD_SCHEMA = ROOT / "control" / "schemas" / "task-record.schema.json"
EVIDENCE = ROOT / "docs" / "evidence"
GOVERNANCE = ROOT / "docs" / "governance"
COMPLETED = {"passed", "pass_with_action"}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_schema(
    value: dict[str, Any], schema_path: Path, label: str, errors: list[str]
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(value):
        location = ".".join(str(part) for part in error.absolute_path)
        errors.append(f"{label} {location}: {error.message}")


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def artifact_exists(relative_path: str) -> bool:
    return (ROOT / relative_path).is_file()


def find_dependency_cycles(tasks: dict[str, dict[str, Any]]) -> list[list[str]]:
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(task_id: str) -> None:
        if state.get(task_id) == 1:
            start = stack.index(task_id)
            cycles.append(stack[start:] + [task_id])
            return
        if state.get(task_id) == 2:
            return
        state[task_id] = 1
        stack.append(task_id)
        for dependency in tasks[task_id]["dependencies"]:
            if dependency in tasks:
                visit(dependency)
        stack.pop()
        state[task_id] = 2

    for task_id in tasks:
        visit(task_id)
    return cycles


def derive_phase_status(phase_tasks: list[dict[str, Any]]) -> str:
    statuses = {task["status"] for task in phase_tasks}
    if "blocked" in statuses:
        return "blocked"
    if "in_progress" in statuses:
        return "in_progress"
    if phase_tasks and statuses <= COMPLETED:
        return "pass_with_action" if "pass_with_action" in statuses else "passed"
    if "ready" in statuses:
        return "ready"
    return "not_started"


def audit() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    control = load_yaml(CONTROL)
    validate_schema(control, CONTROL_SCHEMA, "control", errors)

    phases = {phase["id"]: phase for phase in control.get("phases", [])}
    task_list = control.get("tasks", [])
    tasks = {task["id"]: task for task in task_list}
    action_list = control.get("actions", [])
    actions = {action["id"]: action for action in action_list}
    issue_list = control.get("issues", [])
    issues = {issue["id"]: issue for issue in issue_list}
    final_gates = {gate["id"]: gate for gate in control.get("final_gates", [])}

    for label, values in (
        ("phase", [phase["id"] for phase in control.get("phases", [])]),
        ("task", [task["id"] for task in task_list]),
        ("action", [action["id"] for action in action_list]),
        ("issue", [issue["id"] for issue in issue_list]),
        ("final gate", list(final_gates)),
    ):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(duplicates)}")

    if control.get("current_phase") not in phases:
        errors.append(f"unknown current_phase: {control.get('current_phase')}")

    for task in task_list:
        task_id = task["id"]
        if task["phase"] not in phases:
            errors.append(f"{task_id}: unknown phase {task['phase']}")
        for dependency in task["dependencies"]:
            if dependency not in tasks:
                errors.append(f"{task_id}: unknown dependency {dependency}")
        for action_id in task["residual_actions"]:
            if action_id not in actions:
                errors.append(f"{task_id}: unknown residual action {action_id}")

        if task["status"] in COMPLETED:
            if not task["record"]:
                errors.append(f"{task_id}: completed task has no record")
                continue
            record_path = ROOT / task["record"]
            if not record_path.is_file():
                errors.append(f"{task_id}: missing task record {task['record']}")
                continue
            record = load_yaml(record_path)
            validate_schema(record, RECORD_SCHEMA, f"record {task_id}", errors)
            if record.get("task_id") != task_id:
                errors.append(f"{task_id}: record task_id mismatch")
            if record.get("phase_id") != task["phase"]:
                errors.append(f"{task_id}: record phase mismatch")
            if record.get("outcome") != task["status"]:
                errors.append(f"{task_id}: record outcome mismatch")
            if set(record.get("residual_actions", [])) != set(task["residual_actions"]):
                errors.append(f"{task_id}: record residual actions mismatch")
            for issue_id in record.get("issues", []):
                if issue_id not in issues:
                    errors.append(f"{task_id}: record references unknown issue {issue_id}")
            record_artifacts = list(record.get("deliverables", []))
            for check in record.get("acceptance_checks", []):
                record_artifacts.extend(check.get("evidence", []))
            for artifact in sorted(set(record_artifacts)):
                if not artifact_exists(artifact):
                    errors.append(f"{task_id}: missing record artifact {artifact}")

        if task["status"] == "passed" and task["residual_actions"]:
            errors.append(f"{task_id}: passed task still has residual actions")
        if task["status"] == "pass_with_action":
            if not task["residual_actions"]:
                errors.append(f"{task_id}: pass_with_action has no residual actions")
            for action_id in task["residual_actions"]:
                action = actions.get(action_id)
                if action and action["status"] in {"closed", "waived"}:
                    message = (
                        f"{task_id}: residual action {action_id} is closed; "
                        "rerun evidence and promote task"
                    )
                    errors.append(message)
        for artifact in task["evidence"]:
            if not artifact_exists(artifact):
                errors.append(f"{task_id}: missing task evidence {artifact}")

    for cycle in find_dependency_cycles(tasks):
        errors.append(f"dependency cycle: {' -> '.join(cycle)}")

    tasks_by_phase: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in task_list:
        tasks_by_phase[task["phase"]].append(task)
    for phase_id, phase in phases.items():
        derived = derive_phase_status(tasks_by_phase[phase_id])
        if phase["status"] != derived:
            errors.append(f"{phase_id}: declared status {phase['status']} != derived {derived}")
        if phase["status"] in {"passed", "pass_with_action"}:
            if not phase["exit_record"] or not artifact_exists(phase["exit_record"]):
                errors.append(f"{phase_id}: closed phase has no exit record")

    for action in action_list:
        action_id = action["id"]
        if action["status"] in {"closed", "waived"} and not action["evidence"]:
            errors.append(f"{action_id}: closed/waived action has no evidence")
        for artifact in action["evidence"]:
            if not artifact_exists(artifact):
                errors.append(f"{action_id}: missing evidence {artifact}")

    for issue in issue_list:
        issue_id = issue["id"]
        for task_id in issue["task_ids"]:
            if task_id not in tasks:
                errors.append(f"{issue_id}: unknown task {task_id}")
        for action_id in issue["action_ids"]:
            if action_id not in actions:
                errors.append(f"{issue_id}: unknown action {action_id}")
        if issue["status"] == "resolved":
            if not issue["cause"] or not issue["resolution"] or not issue["evidence"]:
                errors.append(f"{issue_id}: resolved issue lacks cause/resolution/evidence")
        if issue["status"] == "mitigated" and (not issue["resolution"] or not issue["action_ids"]):
            errors.append(f"{issue_id}: mitigated issue lacks mitigation/action")
        for artifact in issue["evidence"]:
            if not artifact_exists(artifact):
                errors.append(f"{issue_id}: missing evidence {artifact}")

    for gate in final_gates.values():
        for task_id in gate["required_task_ids"]:
            if task_id not in tasks:
                errors.append(f"{gate['id']}: unknown required task {task_id}")
        if gate["status"] == "passed" and not gate["evidence"]:
            errors.append(f"{gate['id']}: passed final gate has no evidence")
        for artifact in gate["evidence"]:
            if not artifact_exists(artifact):
                errors.append(f"{gate['id']}: missing evidence {artifact}")

    final_blockers: list[str] = []
    for task in task_list:
        if task["required"] and task["status"] != "passed":
            final_blockers.append(f"task:{task['id']}={task['status']}")
        if task["status"] in COMPLETED and task["record"]:
            record_path = ROOT / task["record"]
            if record_path.is_file():
                review_status = load_yaml(record_path).get("review", {}).get("status")
                if review_status != "accepted":
                    final_blockers.append(f"record-review:{task['id']}={review_status}")
    for action in action_list:
        if action["status"] not in {"closed", "waived"}:
            final_blockers.append(f"action:{action['id']}={action['status']}")
    for issue in issue_list:
        if issue["blocks_final"] and issue["status"] != "resolved":
            final_blockers.append(f"issue:{issue['id']}={issue['status']}")
    for gate in final_gates.values():
        if gate["status"] != "passed":
            final_blockers.append(f"gate:{gate['id']}={gate['status']}")
    for field, value in control["release"].items():
        if not value:
            final_blockers.append(f"release:{field}=missing")

    if control["current_phase"] != "PHASE-08":
        warnings.append(
            f"current phase is {control['current_phase']}; final acceptance remains NOT_READY"
        )

    counts = {
        "phases": Counter(phase["status"] for phase in phases.values()),
        "tasks": Counter(task["status"] for task in task_list),
        "actions": Counter(action["status"] for action in action_list),
        "issues": Counter(issue["status"] for issue in issue_list),
        "final_gates": Counter(gate["status"] for gate in final_gates.values()),
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "structural_status": "PASS" if not errors else "FAIL",
        "final_readiness": "READY" if not errors and not final_blockers else "NOT_READY",
        "current_phase": control["current_phase"],
        "counts": {name: dict(values) for name, values in counts.items()},
        "errors": errors,
        "warnings": warnings,
        "final_blockers": final_blockers,
        "control": control,
    }


def render_board(report: dict[str, Any]) -> str:
    control = report["control"]
    lines = [
        "# 项目统一控制板",
        "",
        "> 本文件由 `scripts/control_plane.py` 从 "
        "`control/project-control.yaml` 生成；请勿手工修改状态。",
        "",
        f"- 结构校验：`{report['structural_status']}`",
        f"- 最终验收就绪度：`{report['final_readiness']}`",
        f"- 当前阶段：`{report['current_phase']}`",
        f"- 最近审计：`{report['generated_at']}`",
        "",
        "## 阶段",
        "",
        "| Phase | 名称 | 状态 | 退出记录 |",
        "|---|---|---|---|",
    ]
    for phase in control["phases"]:
        record = phase["exit_record"] or "—"
        lines.append(f"| {phase['id']} | {phase['title']} | `{phase['status']}` | {record} |")

    lines.extend(["", "## 当前可开始任务", ""])
    ready = [task for task in control["tasks"] if task["status"] == "ready"]
    if ready:
        lines.extend(
            f"- `{task['id']}` {task['title']}（Owner: {task['owner']}）" for task in ready
        )
    else:
        lines.append("- 无")

    lines.extend(
        [
            "",
            "## 全部任务",
            "",
            "| Phase | Task | 任务 | Owner | 状态 | 完成记录 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for task in control["tasks"]:
        record = task["record"] or "—"
        task_cells = (
            task["phase"],
            task["id"],
            task["title"],
            task["owner"],
            task["status"],
            record,
        )
        lines.append("| {} | {} | {} | {} | `{}` | {} |".format(*task_cells))

    lines.extend(
        ["", "## 开放行动", "", "| ID | 行动 | Owner | 截止 | 阻断 |", "|---|---|---|---|---|"]
    )
    open_actions = [
        action for action in control["actions"] if action["status"] not in {"closed", "waived"}
    ]
    for action in open_actions:
        blocked_tasks = ", ".join(action["blocks"])
        lines.append(
            f"| {action['id']} | {action['title']} | {action['owner']} | "
            f"{action['deadline']} | {blocked_tasks} |"
        )
    if not open_actions:
        lines.append("| — | 无 | — | — | — |")

    lines.extend(
        [
            "",
            "## 未关闭问题",
            "",
            "| ID | 状态 | 严重度 | 现象 | 后续行动 |",
            "|---|---|---|---|---|",
        ]
    )
    open_issues = [issue for issue in control["issues"] if issue["status"] != "resolved"]
    for issue in open_issues:
        follow_up = ", ".join(issue["action_ids"]) or "—"
        lines.append(
            f"| {issue['id']} | `{issue['status']}` | {issue['severity']} | "
            f"{issue['symptom']} | {follow_up} |"
        )
    if not open_issues:
        lines.append("| — | — | — | 无 | — |")

    task_counts = report["counts"]["tasks"]
    lines.extend(
        [
            "",
            "## 任务状态计数",
            "",
            *[f"- {status}: {count}" for status, count in sorted(task_counts.items())],
            "",
            "## 最终验收",
            "",
            f"当前共有 `{len(report['final_blockers'])}` 个机器判定阻断项。"
            "完整清单见 `docs/evidence/control-plane-validation.md`。",
            "",
            "| Gate | 验收项 | 状态 |",
            "|---|---|---|",
        ]
    )
    for gate in control["final_gates"]:
        lines.append(f"| {gate['id']} | {gate['title']} | `{gate['status']}` |")
    lines.append("")
    return "\n".join(lines)


def render_issue_log(report: dict[str, Any]) -> str:
    lines = [
        "# 问题与解决统一日志",
        "",
        "> 真值来自 `control/project-control.yaml`。问题不删除；解决后保留原因、处理和证据。",
        "",
    ]
    for issue in report["control"]["issues"]:
        lines.extend(
            [
                f"## {issue['id']} · {issue['status'].upper()}",
                "",
                f"- 发现时间：{issue['discovered_at']}",
                f"- 阶段/任务：{issue['phase']} / {', '.join(issue['task_ids'])}",
                f"- 严重度：{issue['severity']}；阻断最终验收：{issue['blocks_final']}",
                f"- 现象：{issue['symptom']}",
                f"- 原因：{issue['cause'] or '尚未确认'}",
                f"- 解决/缓解：{issue['resolution'] or '尚未处理'}",
                f"- 行动：{', '.join(issue['action_ids']) or '无'}",
                f"- 证据：{', '.join(issue['evidence']) or '尚无'}",
                "",
            ]
        )
    return "\n".join(lines)


def write_outputs(report: dict[str, Any]) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    GOVERNANCE.mkdir(parents=True, exist_ok=True)
    public_report = {key: value for key, value in report.items() if key != "control"}
    (EVIDENCE / "control-plane-validation.json").write_text(
        json.dumps(public_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_lines = [
        "# Control Plane Validation",
        "",
        f"- Structural status: `{report['structural_status']}`",
        f"- Final readiness: `{report['final_readiness']}`",
        f"- Current phase: `{report['current_phase']}`",
        f"- Generated: `{report['generated_at']}`",
        "",
        "## Counts",
        "",
    ]
    for group, counts in report["counts"].items():
        md_lines.append(f"- {group}: {json.dumps(counts, ensure_ascii=False, sort_keys=True)}")
    md_lines.extend(["", "## Structural errors", ""])
    md_lines.extend(f"- {error}" for error in report["errors"] or ["None"])
    md_lines.extend(["", "## Warnings", ""])
    md_lines.extend(f"- {warning}" for warning in report["warnings"] or ["None"])
    md_lines.extend(["", "## Final blockers", ""])
    md_lines.extend(f"- `{blocker}`" for blocker in report["final_blockers"] or ["None"])
    md_lines.append("")
    (EVIDENCE / "control-plane-validation.md").write_text("\n".join(md_lines), encoding="utf-8")
    (GOVERNANCE / "CONTROL_BOARD.md").write_text(render_board(report), encoding="utf-8")
    (GOVERNANCE / "ISSUE_LOG.md").write_text(render_issue_log(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-final",
        action="store_true",
        help="also fail when the project is not ready for final acceptance",
    )
    args = parser.parse_args()
    report = audit()
    write_outputs(report)
    print(
        json.dumps(
            {
                "structural_status": report["structural_status"],
                "final_readiness": report["final_readiness"],
                "current_phase": report["current_phase"],
                "errors": len(report["errors"]),
                "final_blockers": len(report["final_blockers"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if report["structural_status"] != "PASS":
        return 1
    if args.check_final and report["final_readiness"] != "READY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
