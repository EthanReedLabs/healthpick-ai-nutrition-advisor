from __future__ import annotations

from scripts.control_plane import COMPLETED, ROOT, audit, render_board


def test_control_plane_is_structurally_valid() -> None:
    report = audit()
    assert report["structural_status"] == "PASS"
    assert report["errors"] == []


def test_completed_tasks_have_individual_records() -> None:
    report = audit()
    completed = [
        task for task in report["control"]["tasks"] if task["status"] in COMPLETED
    ]
    assert completed
    for task in completed:
        assert task["record"]
        assert (ROOT / task["record"]).is_file()


def test_final_gate_stays_closed_while_work_remains() -> None:
    report = audit()
    assert report["final_readiness"] == "NOT_READY"
    assert "action:ACTION-01=open" in report["final_blockers"]
    assert "task:P03-01=ready" in report["final_blockers"]
    assert "gate:FINAL-10=not_started" in report["final_blockers"]


def test_non_release_environment_issue_does_not_fake_or_block_release() -> None:
    report = audit()
    assert "issue:ISSUE-009=open" not in report["final_blockers"]
    assert "issue:ISSUE-006=mitigated" in report["final_blockers"]


def test_generated_board_lists_every_task_and_final_gate() -> None:
    report = audit()
    board = render_board(report)
    for task in report["control"]["tasks"]:
        assert f"| {task['phase']} | {task['id']} |" in board
    for gate in report["control"]["final_gates"]:
        assert f"| {gate['id']} |" in board
