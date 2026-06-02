"""Unified CLI — python -m factory <command>

Commands:
  create   สร้าง standalone company project ที่ path ที่เลือก
  run      รัน 1 daily cycle (lookup path จาก registry)
  list     ดูบริษัทที่สร้างแล้วทั้งหมด (registry)
  status   ดูสถานะ + memory stats
  delete   ลบบริษัท + ออกจาก registry
"""
import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m factory",
        description="AI Company Factory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m factory create --template trading --name myfund --output-dir D:\\projects\n"
            "  python -m factory run    --company myfund\n"
            "  python -m factory list\n"
            "  python -m factory status --company myfund\n"
            "  python -m factory delete --company myfund\n"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    sub.required = True

    # create
    p = sub.add_parser("create", help="Create a standalone company project")
    p.add_argument("--template",        required=True, metavar="ID")
    p.add_argument("--name",            required=True)
    p.add_argument("--risk-level",      default="low", choices=["low", "medium", "high"])
    p.add_argument("--initial-capital", type=float, default=0)
    p.add_argument("--output-dir",      required=True,
                   help="Directory where the company project folder will be created")

    # run
    p = sub.add_parser("run", help="Run one daily cycle")
    p.add_argument("--company", required=True)
    p.add_argument("--date",    default=None)
    p.add_argument("--mock",    action="store_true", help="Force MockLLM")

    # list
    sub.add_parser("list", help="List all registered companies")

    # status
    p = sub.add_parser("status", help="Show company status and memory stats")
    p.add_argument("--company", required=True)

    # delete
    p = sub.add_parser("delete", help="Delete a company and remove from registry")
    p.add_argument("--company", required=True)
    p.add_argument("--yes", "-y", action="store_true")

    return parser


def main() -> int:
    from factory.config import setup_logging
    setup_logging()

    parser = _build_parser()
    args = parser.parse_args()

    if args.cmd == "create":
        from pathlib import Path
        from factory.create import create
        from factory.errors import ValidationError, CollisionError
        inputs = {
            "name": args.name,
            "risk_level": args.risk_level,
            "initial_capital": args.initial_capital,
        }
        try:
            instance = create(args.template, inputs, output_dir=Path(args.output_dir))
            print(f"[OK] Created: {instance.path}")
            print(f"  cd {instance.path}")
            print(f"  python run_cycle.py --mock   # test without API key")
            return 0
        except (ValidationError, CollisionError) as e:
            print(f"[ERROR] {e}")
            return 1

    elif args.cmd == "run":
        from factory.run import run_cycle
        from factory.errors import BudgetExceeded

        llm = None
        if args.mock:
            from factory.llm.mock import MockLLMClient
            llm = MockLLMClient()
            print("[INFO] MockLLM mode")

        try:
            result = run_cycle(args.company, date=args.date, llm=llm)
            print(f"\n[OK] Cycle complete for '{result.company}' on {result.date}")
            return 0
        except FileNotFoundError as e:
            print(f"[ERROR] {e}")
            return 1
        except BudgetExceeded as e:
            print(f"[BUDGET] {e}")
            return 2

    elif args.cmd == "list":
        from factory.cmd_list import run_list
        return run_list()

    elif args.cmd == "status":
        from factory.cmd_status import run_status
        return run_status(args.company)

    elif args.cmd == "delete":
        from factory.cmd_delete import run_delete
        return run_delete(args.company, yes=args.yes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
