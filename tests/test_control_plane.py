from __future__ import annotations

from copy import deepcopy

import scripts.control_plane as control_plane
from scripts.control_plane import COMPLETED, ROOT, audit, render_board


def test_control_plane_is_structurally_valid() -> None:
    report = audit()
    assert report["structural_status"] == "PASS"
    assert report["errors"] == []


def test_completed_tasks_have_individual_records() -> None:
    report = audit()
    completed = [task for task in report["control"]["tasks"] if task["status"] in COMPLETED]
    assert completed
    for task in completed:
        assert task["record"]
        assert (ROOT / task["record"]).is_file()


def test_final_gate_stays_closed_while_work_remains(monkeypatch) -> None:
    control = deepcopy(audit()["control"])
    next(task for task in control["tasks"] if task["id"] == "P08-07")["status"] = (
        "in_progress"
    )
    phase = next(phase for phase in control["phases"] if phase["id"] == "PHASE-08")
    phase["status"] = "in_progress"
    phase["exit_record"] = None
    next(gate for gate in control["final_gates"] if gate["id"] == "FINAL-10")[
        "status"
    ] = "not_started"

    original_load_yaml = control_plane.load_yaml

    def load_simulated_control(path):
        if path == control_plane.CONTROL:
            return control
        return original_load_yaml(path)

    monkeypatch.setattr(control_plane, "load_yaml", load_simulated_control)
    report = control_plane.audit()
    assert report["final_readiness"] == "NOT_READY"
    assert report["final_blockers"]
    assert any(blocker.startswith("task:") for blocker in report["final_blockers"])
    assert "gate:FINAL-10=not_started" in report["final_blockers"]


def test_signed_release_is_finally_ready() -> None:
    report = audit()
    assert report["final_readiness"] == "READY"
    assert report["final_blockers"] == []


def test_non_release_environment_issue_does_not_fake_or_block_release() -> None:
    report = audit()
    assert "issue:ISSUE-009=open" not in report["final_blockers"]
    blocking_issues = [
        issue
        for issue in report["control"]["issues"]
        if issue["blocks_final"] and issue["status"] != "resolved"
    ]
    for issue in blocking_issues:
        assert f"issue:{issue['id']}={issue['status']}" in report["final_blockers"]


def test_generated_board_lists_every_task_and_final_gate() -> None:
    report = audit()
    board = render_board(report)
    for task in report["control"]["tasks"]:
        assert f"| {task['phase']} | {task['id']} |" in board
    for gate in report["control"]["final_gates"]:
        assert f"| {gate['id']} |" in board
