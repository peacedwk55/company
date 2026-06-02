import shutil
from pathlib import Path
from factory.registry import registry


def run_delete(company_name: str, *, yes: bool = False) -> int:
    record = registry.get(company_name)
    if not record:
        print(f"[ERROR] '{company_name}' not found in registry.")
        return 1

    company_dir = Path(record.path)
    print(f"  Company  : {company_name}")
    print(f"  Path     : {record.path}")
    print(f"  Template : {record.template}")
    print(f"  Created  : {record.created_at[:10]}")

    briefings_dir = company_dir / "memory" / "briefings"
    briefs = list(briefings_dir.glob("*.md")) if briefings_dir.exists() else []
    print(f"  Briefs   : {len(briefs)} daily brief(s) will be lost")
    print()

    if not yes:
        try:
            answer = input(f"  Delete '{company_name}' permanently? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return 0
        if answer != "y":
            print("  Cancelled.")
            return 0

    if company_dir.exists():
        shutil.rmtree(company_dir)
        print(f"  [OK] Deleted folder: {record.path}")
    else:
        print(f"  [WARN] Folder not found: {record.path}")

    registry.remove(company_name)
    print(f"  [OK] Removed '{company_name}' from registry.")
    return 0
