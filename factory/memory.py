import re
import logging
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock

log = logging.getLogger(__name__)

# Matches <!-- id: X | ts: Y | agent: Z --> ... <!-- /id: X -->
_ENTRY_RE = re.compile(
    r"<!-- id: (?P<id>\S+) \| ts: (?P<ts>\S+) \| agent: (?P<agent>\S+) -->\n"
    r"(?P<body>.*?)\n"
    r"<!-- /id: (?P=id) -->",
    re.DOTALL,
)

_KIND_RE = re.compile(r"^(?P<kind>[a-z]+)-\d{8}-\d+$")


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    ts: str
    agent: str
    kind: str
    body: str


class MemoryManager:
    def __init__(self, company_dir: Path, *, date: str | None = None) -> None:
        """
        company_dir: root of the company instance (e.g. companies/myfund/)
        date: YYYYMMDD string injected for determinism; None → read from clock
        """
        self._dir = Path(company_dir) / "memory"
        self._date = date  # injected from run_cycle for deterministic testing

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _current_date(self) -> str:
        if self._date:
            return self._date
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    def _current_ts(self) -> str:
        if self._date:
            d = self._date
            return f"{d[:4]}-{d[4:6]}-{d[6:]}T00:00:00Z"
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _path(self, file: str) -> Path:
        p = self._dir / file
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _lock(self, file: str) -> FileLock:
        lock_path = self._dir / f".{file}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        return FileLock(str(lock_path))

    # ------------------------------------------------------------------
    # Core API (§13.1)
    # ------------------------------------------------------------------

    def next_id(self, kind: str, date: str | None = None) -> str:
        """Generate the next sequential ID: {kind}-{YYYYMMDD}-{NNN}"""
        date = date or self._current_date()
        prefix = f"{kind}-{date}-"
        count = 0
        if self._dir.exists():
            for md_file in self._dir.glob("*.md"):
                try:
                    text = md_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                for m in _ENTRY_RE.finditer(text):
                    if m.group("id").startswith(prefix):
                        count += 1
        return f"{prefix}{count + 1:03d}"

    def append(self, file: str, body: str, *, agent: str, kind: str) -> MemoryEntry:
        """Append a new entry (append-only; never overwrites existing).

        Thread-safe via per-file FileLock.
        Entry format follows §14.7.
        """
        ts = self._current_ts()
        date = self._current_date()
        entry_id = self.next_id(kind, date=date)
        block = (
            f"\n<!-- id: {entry_id} | ts: {ts} | agent: {agent} -->\n"
            f"{body.strip()}\n"
            f"<!-- /id: {entry_id} -->\n"
        )
        path = self._path(file)
        with self._lock(file):
            with open(path, "a", encoding="utf-8") as f:
                f.write(block)
        log.debug("memory: appended %s to %s", entry_id, file)
        return MemoryEntry(id=entry_id, ts=ts, agent=agent, kind=kind, body=body.strip())

    def read(self, file: str) -> str:
        """Return raw text of a memory file (empty string if not found)."""
        path = self._path(file)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def entries(self, file: str) -> list[MemoryEntry]:
        """Parse and return all deduplicated entries from a memory file."""
        text = self.read(file)
        result: list[MemoryEntry] = []
        seen: set[str] = set()
        for m in _ENTRY_RE.finditer(text):
            entry_id = m.group("id")
            if entry_id in seen:
                continue
            seen.add(entry_id)
            kind_m = _KIND_RE.match(entry_id)
            kind = kind_m.group("kind") if kind_m else "unknown"
            result.append(MemoryEntry(
                id=entry_id,
                ts=m.group("ts"),
                agent=m.group("agent"),
                kind=kind,
                body=m.group("body").strip(),
            ))
        return result

    # ------------------------------------------------------------------
    # Task CRUD (M3 — stored in task_queue.md as append-only entries)
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        *,
        agent: str,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> MemoryEntry:
        parts = [f"Title: {title}", f"Priority: {priority}", "Status: Open"]
        if due_date:
            parts.append(f"Due: {due_date}")
        body = "\n".join(parts)
        return self.append("task_queue.md", body, agent=agent, kind="task")

    def update_task(self, task_id: str, *, status: str, agent: str = "system") -> MemoryEntry:
        """Append a status-update entry (append-only; original entry kept)."""
        body = f"Update → {task_id}: status changed to {status}"
        return self.append("task_queue.md", body, agent=agent, kind="taskupdate")

    def open_tasks(self) -> list[MemoryEntry]:
        """Return task entries that have Status: Open and no closure update."""
        all_entries = self.entries("task_queue.md")
        tasks = [e for e in all_entries if e.kind == "task" and "Status: Open" in e.body]
        closed_ids = {
            e.body.split("→ ", 1)[1].split(":")[0].strip()
            for e in all_entries
            if e.kind == "taskupdate" and "Completed" in e.body
        }
        return [t for t in tasks if t.id not in closed_ids]
