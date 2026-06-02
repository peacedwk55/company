import json
import pytest
from pathlib import Path
from factory.create import create
from factory.errors import ValidationError, CollisionError


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


# ------------------------------------------------------------------
# Happy path
# ------------------------------------------------------------------

def test_create_produces_correct_folder_structure(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    p = instance.path
    assert p.is_dir()
    assert (p / "company.yaml").exists()
    assert (p / "agents.yaml").exists()
    assert (p / "workflow.yaml").exists()
    assert (p / "constitution.md").exists()
    assert (p / ".manifest.json").exists()
    assert (p / "DISCLAIMER.md").exists()
    assert (p / "logs").is_dir()
    assert (p / "run_cycle.py").exists()
    assert (p / "README.md").exists()
    assert (p / ".env.template").exists()
    assert (p / "pyproject.toml").exists()


def test_create_initialises_memory_files(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    mem = instance.path / "memory"
    assert mem.is_dir()
    assert (mem / "observations.md").exists()
    assert (mem / "risk_log.md").exists()
    assert (mem / "task_queue.md").exists()
    assert (mem / "hypotheses.md").exists()
    assert (mem / "decisions.md").exists()
    assert (mem / "briefings").is_dir()


def test_manifest_contains_provenance(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund", "risk_level": "low"},
                      output_dir=output_dir, register=False)
    manifest = json.loads((instance.path / ".manifest.json").read_text())
    assert manifest["template_id"] == "trading"
    assert manifest["name"] == "myfund"
    assert "created_at" in manifest
    assert manifest["inputs"]["risk_level"] == "low"


def test_placeholders_rendered_in_company_yaml(output_dir: Path) -> None:
    instance = create("trading", {"name": "testco", "risk_level": "medium"},
                      output_dir=output_dir, register=False)
    text = (instance.path / "company.yaml").read_text()
    assert "testco" in text
    assert "medium" in text
    assert "{{" not in text


def test_placeholders_rendered_in_constitution(output_dir: Path) -> None:
    instance = create("trading", {"name": "testco"}, output_dir=output_dir, register=False)
    text = (instance.path / "constitution.md").read_text()
    assert "testco" in text
    assert "{{" not in text


def test_default_risk_level_is_low(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    manifest = json.loads((instance.path / ".manifest.json").read_text())
    assert manifest["inputs"]["risk_level"] == "low"


def test_default_execution_mode_is_paper(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    text = (instance.path / "company.yaml").read_text()
    assert "paper" in text


def test_run_cycle_py_contains_company_name(output_dir: Path) -> None:
    instance = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    text = (instance.path / "run_cycle.py").read_text()
    assert "myfund" in text


# ------------------------------------------------------------------
# Validation errors — no folder created
# ------------------------------------------------------------------

def test_invalid_name_pattern_raises(output_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc_info:
        create("trading", {"name": "INVALID NAME!"}, output_dir=output_dir, register=False)
    assert "name" in str(exc_info.value)


def test_name_too_short_raises(output_dir: Path) -> None:
    with pytest.raises(ValidationError):
        create("trading", {"name": "ab"}, output_dir=output_dir, register=False)


def test_invalid_risk_level_raises(output_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc_info:
        create("trading", {"name": "myfund", "risk_level": "extreme"},
               output_dir=output_dir, register=False)
    assert "risk_level" in str(exc_info.value)


def test_negative_capital_raises(output_dir: Path) -> None:
    with pytest.raises(ValidationError) as exc_info:
        create("trading", {"name": "myfund", "initial_capital": -1000},
               output_dir=output_dir, register=False)
    assert "initial_capital" in str(exc_info.value)


def test_validation_error_creates_no_folder(output_dir: Path) -> None:
    with pytest.raises(ValidationError):
        create("trading", {"name": "AB!!"}, output_dir=output_dir, register=False)
    assert not (output_dir / "AB!!").exists()


# ------------------------------------------------------------------
# Collision detection
# ------------------------------------------------------------------

def test_collision_raises_error(output_dir: Path) -> None:
    create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    with pytest.raises(CollisionError):
        create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)


def test_collision_does_not_corrupt_existing(output_dir: Path) -> None:
    first = create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    original = (first.path / ".manifest.json").read_text()
    try:
        create("trading", {"name": "myfund"}, output_dir=output_dir, register=False)
    except CollisionError:
        pass
    assert (first.path / ".manifest.json").read_text() == original
