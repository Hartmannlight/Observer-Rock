from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_implementation_roadmap_exists_with_tdd_sections() -> None:
    roadmap_path = PROJECT_ROOT / ".ai" / "IMPLEMENTATION_ROADMAP.md"

    assert roadmap_path.exists()
    contents = roadmap_path.read_text(encoding="utf-8")

    assert "# Observer Rock Implementation Roadmap" in contents
    assert "## TDD Workflow" in contents
    assert "## Test Architecture" in contents
    assert "## Agent Workflow" in contents


def test_task_backlog_exists_with_tdd_task_template() -> None:
    backlog_path = PROJECT_ROOT / ".ai" / "TASK_BACKLOG.md"

    assert backlog_path.exists()
    contents = backlog_path.read_text(encoding="utf-8")

    assert "# Observer Rock Task Backlog" in contents
    assert "First failing test" in contents
    assert "Verification commands" in contents
    assert "Status: todo" in contents
