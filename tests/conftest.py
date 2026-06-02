import pytest
from pathlib import Path
from factory.llm.mock import MockLLMClient


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def templates_dir() -> Path:
    return Path(__file__).parent.parent / "templates"


@pytest.fixture
def company_dir(tmp_path: Path) -> Path:
    d = tmp_path / "company"
    d.mkdir()
    return d
