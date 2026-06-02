from pathlib import Path
from factory.registry import registry


def run_list() -> int:
    records = registry.all()

    if not records:
        print("\n  No companies registered yet.")
        print("  Create one: python -m factory create --template trading --name myco --output-dir PATH\n")
        return 0

    print()
    print(f"  {'COMPANY':<18} {'TEMPLATE':<10} {'CREATED':<12} {'LAST RUN':<12} {'PATH'}")
    print("  " + "-" * 80)

    for r in sorted(records, key=lambda x: x.name):
        company_dir = Path(r.path)
        briefings_dir = company_dir / "memory" / "briefings"
        briefs = sorted(briefings_dir.glob("*.md")) if briefings_dir.exists() else []
        last_run = briefs[-1].stem if briefs else "never"
        exists = "[OK]" if company_dir.exists() else "[MISSING]"
        print(f"  {r.name:<18} {r.template:<10} {r.created_at[:10]:<12} {last_run:<12} {r.path} {exists}")

    print()
    print(f"  Total: {len(records)} company/companies")
    print()
    return 0
