"""Registry of companies created by this factory.

Stores name, template, output path, and creation date.
File: factory_registry.json at project root.
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path

from factory.config import _ROOT

REGISTRY_FILE = _ROOT / "factory_registry.json"


@dataclass
class CompanyRecord:
    name: str
    template: str
    path: str          # absolute path to the standalone project
    created_at: str
    version: float = 1.0


class Registry:
    def __init__(self, path: Path = REGISTRY_FILE) -> None:
        self._path = path

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8")).get("companies", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, records: list[dict]) -> None:
        self._path.write_text(
            json.dumps({"companies": records}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, record: CompanyRecord) -> None:
        records = self._load()
        records = [r for r in records if r["name"] != record.name]
        records.append(asdict(record))
        self._save(records)

    def all(self) -> list[CompanyRecord]:
        return [CompanyRecord(**r) for r in self._load()]

    def get(self, name: str) -> CompanyRecord | None:
        for r in self._load():
            if r["name"] == name:
                return CompanyRecord(**r)
        return None

    def remove(self, name: str) -> bool:
        records = self._load()
        new = [r for r in records if r["name"] != name]
        if len(new) == len(records):
            return False
        self._save(new)
        return True


registry = Registry()
