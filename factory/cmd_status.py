import json
import yaml
from pathlib import Path
from factory.registry import registry
from factory.memory import MemoryManager


def run_status(company_name: str) -> int:
    record = registry.get(company_name)
    if not record:
        print(f"[ERROR] '{company_name}' not found in registry.")
        print("  Run: python -m factory list")
        return 1

    company_dir = Path(record.path)
    if not company_dir.exists():
        print(f"[ERROR] Path missing: {record.path}")
        print("  The project folder was moved or deleted.")
        return 1

    manifest_path = company_dir / ".manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    company_yaml = company_dir / "company.yaml"
    company = yaml.safe_load(company_yaml.read_text(encoding="utf-8")) if company_yaml.exists() else {}

    mm = MemoryManager(company_dir)
    mem_stats = [
        ("observations", len(mm.entries("observations.md"))),
        ("hypotheses",   len(mm.entries("hypotheses.md"))),
        ("decisions",    len(mm.entries("decisions.md"))),
        ("risk_log",     len(mm.entries("risk_log.md"))),
        ("open tasks",   len(mm.open_tasks())),
    ]

    briefings_dir = company_dir / "memory" / "briefings"
    briefs = sorted(briefings_dir.glob("*.md")) if briefings_dir.exists() else []

    print()
    print(f"  {'=' * 48}")
    print(f"  Company  : {company_name}")
    print(f"  {'=' * 48}")
    print(f"  Template : {manifest.get('template_id', '?')} v{manifest.get('template_version', '?')}")
    print(f"  Created  : {manifest.get('created_at', '?')[:10]}")
    print(f"  Path     : {record.path}")
    print(f"  Mode     : {company.get('execution_mode', '?')}")
    print(f"  Risk     : {company.get('risk_level', '?')}")
    print()
    print(f"  Memory")
    print(f"  {'-' * 32}")
    for label, count in mem_stats:
        bar = "#" * min(count, 20)
        print(f"  {label:<16}: {count:>4}  {bar}")
    print()
    print(f"  Daily Briefs : {len(briefs)} total")

    if briefs:
        last = briefs[-1]
        print(f"  Last run     : {last.stem}")
        print()
        lines = last.read_text(encoding="utf-8").splitlines()
        summary = [l for l in lines if l.startswith("- **[") or l.startswith("## ")]
        print(f"  --- Preview: {last.name} ---")
        for line in summary[:6]:
            print(f"  {line}")
    else:
        print(f"  Last run     : never")
        print(f"  To run:  cd {record.path} && python run_cycle.py")

    print()
    return 0
