import pytest
from pathlib import Path
from factory.memory import MemoryManager


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mm(tmp_path: Path) -> MemoryManager:
    return MemoryManager(tmp_path, date="20260601")


# ------------------------------------------------------------------
# append() + read()
# ------------------------------------------------------------------

def test_append_creates_file(mm: MemoryManager) -> None:
    mm.append("observations.md", "First observation", agent="analyst", kind="obs")
    assert (mm._dir / "observations.md").exists()


def test_append_returns_entry_with_correct_id(mm: MemoryManager) -> None:
    entry = mm.append("observations.md", "Test obs", agent="analyst", kind="obs")
    assert entry.id == "obs-20260601-001"
    assert entry.agent == "analyst"
    assert entry.kind == "obs"
    assert entry.body == "Test obs"


def test_read_contains_body(mm: MemoryManager) -> None:
    mm.append("observations.md", "Hello world", agent="analyst", kind="obs")
    text = mm.read("observations.md")
    assert "Hello world" in text


def test_read_returns_empty_for_missing_file(mm: MemoryManager) -> None:
    assert mm.read("nonexistent.md") == ""


# ------------------------------------------------------------------
# Append-only: never overwrites
# ------------------------------------------------------------------

def test_append_only_preserves_original(mm: MemoryManager) -> None:
    mm.append("observations.md", "Original", agent="analyst", kind="obs")
    mm.append("observations.md", "Second", agent="analyst", kind="obs")
    text = mm.read("observations.md")
    assert "Original" in text
    assert "Second" in text


def test_sequential_ids_increment(mm: MemoryManager) -> None:
    e1 = mm.append("observations.md", "One", agent="a", kind="obs")
    e2 = mm.append("observations.md", "Two", agent="a", kind="obs")
    assert e1.id == "obs-20260601-001"
    assert e2.id == "obs-20260601-002"


# ------------------------------------------------------------------
# entries() — parsing + deduplication
# ------------------------------------------------------------------

def test_entries_returns_all_entries(mm: MemoryManager) -> None:
    mm.append("observations.md", "Alpha", agent="analyst", kind="obs")
    mm.append("observations.md", "Beta", agent="analyst", kind="obs")
    entries = mm.entries("observations.md")
    assert len(entries) == 2
    assert entries[0].body == "Alpha"
    assert entries[1].body == "Beta"


def test_entries_deduplicates_identical_id(tmp_path: Path) -> None:
    mm = MemoryManager(tmp_path, date="20260601")
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    block = (
        "<!-- id: obs-20260601-001 | ts: 2026-06-01T00:00:00Z | agent: analyst -->\n"
        "Duplicate body\n"
        "<!-- /id: obs-20260601-001 -->\n"
    )
    (mem_dir / "observations.md").write_text(block + block, encoding="utf-8")
    entries = mm.entries("observations.md")
    assert len(entries) == 1


def test_entries_empty_for_missing_file(mm: MemoryManager) -> None:
    assert mm.entries("missing.md") == []


def test_entry_kind_parsed_from_id(mm: MemoryManager) -> None:
    entry = mm.append("hypotheses.md", "Market will rise", agent="research", kind="hyp")
    parsed = mm.entries("hypotheses.md")
    assert parsed[0].kind == "hyp"


# ------------------------------------------------------------------
# next_id()
# ------------------------------------------------------------------

def test_next_id_format(mm: MemoryManager) -> None:
    nid = mm.next_id("obs")
    assert nid == "obs-20260601-001"


def test_next_id_increments_after_append(mm: MemoryManager) -> None:
    mm.append("observations.md", "X", agent="a", kind="obs")
    nid = mm.next_id("obs")
    assert nid == "obs-20260601-002"


# ------------------------------------------------------------------
# Task CRUD (M3)
# ------------------------------------------------------------------

def test_create_task_stored_in_queue(mm: MemoryManager) -> None:
    entry = mm.create_task("Write tests", agent="system", priority="high")
    assert entry.kind == "task"
    assert "Write tests" in entry.body
    assert "Status: Open" in entry.body
    assert "Priority: high" in entry.body


def test_create_task_with_due_date(mm: MemoryManager) -> None:
    entry = mm.create_task("Deploy", agent="system", due_date="2026-06-15")
    assert "Due: 2026-06-15" in entry.body


def test_open_tasks_returns_unclosed(mm: MemoryManager) -> None:
    mm.create_task("Task A", agent="system")
    mm.create_task("Task B", agent="system")
    open_t = mm.open_tasks()
    assert len(open_t) == 2


def test_update_task_marks_completion(mm: MemoryManager) -> None:
    task = mm.create_task("Task X", agent="system")
    mm.update_task(task.id, status="Completed", agent="system")
    open_t = mm.open_tasks()
    assert all(t.id != task.id for t in open_t)
