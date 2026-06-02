import json
import shutil
import tempfile
import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

import yaml

from factory.errors import CollisionError, ValidationError
from factory.templates import Template
from factory.config import TEMPLATES_DIR

log = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "# DISCLAIMER\n\n"
    "ระบบนี้เป็นเครื่องมือ research/automation ไม่ใช่คำแนะนำการลงทุน\n\n"
    "ผู้ใช้รับผิดชอบความเสี่ยงเอง\n"
    "ต้องมีใบอนุญาตตามกฎหมายท้องถิ่นก่อนใช้เงินจริง\n\n"
    "This system is a research and automation tool, NOT investment advice.\n"
    "The user bears all financial risk. Obtain required local licenses before live trading.\n"
)


@dataclass
class CompanyInstance:
    name: str
    path: Path
    manifest: dict


def create(
    template_id: str,
    inputs: dict,
    *,
    output_dir: Path,
    register: bool = True,
) -> CompanyInstance:
    """Generate a standalone company project at output_dir/name.

    The generated project is self-contained:
    - run_cycle.py  → python run_cycle.py (run daily cycle)
    - start.py      → placeholder for company dashboard
    - pyproject.toml, .env.template, README.md
    - All config yaml + memory structure

    After creation, registers the company in factory_registry.json.
    """
    template = Template.load(template_id, templates_dir=TEMPLATES_DIR)
    validated = template.validate_inputs(inputs)
    name: str = validated["name"]
    rendered = template.render(validated)

    company_dir = Path(output_dir) / name
    if company_dir.exists():
        raise CollisionError(name)

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp) / name
        tmp.mkdir()

        # Template files (yaml, md, etc.)
        for filename, content in rendered.items():
            (tmp / filename).write_text(content, encoding="utf-8")

        # Memory structure
        _init_memory(tmp, template)

        # Logs dir
        (tmp / "logs").mkdir()

        # Manifest
        manifest = {
            "name": name,
            "template_id": template_id,
            "template_version": template.meta.get("version", 1.0),
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "inputs": validated,
        }
        (tmp / ".manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        if template.meta.get("requires_disclaimer", False):
            (tmp / "DISCLAIMER.md").write_text(DISCLAIMER_TEXT, encoding="utf-8")

        # Standalone runner files
        _write_standalone_files(tmp, name, template_id)

        # Atomic move
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), str(company_dir))

    log.info("Created standalone project '%s' at %s", name, company_dir)

    # Register in factory registry
    if register:
        from factory.registry import registry, CompanyRecord
        registry.add(CompanyRecord(
            name=name,
            template=template_id,
            path=str(company_dir.resolve()),
            created_at=manifest["created_at"],
            version=float(template.meta.get("version", 1.0)),
        ))

    return CompanyInstance(name=name, path=company_dir, manifest=manifest)


# ── AI-generated company (from description) ───────────────────────

def create_from_description(
    description: str,
    name: str,
    *,
    output_dir: Path,
    agent_count: int = 3,
    work_style: str = "balanced",
    risk_level: str = "low",
    llm=None,
    register: bool = True,
    on_progress=None,
) -> CompanyInstance:
    """Generate a company from natural language description using Claude, then create project.

    on_progress: optional callable({type, message}) for streaming progress to WebSocket.
    """
    from factory.generator import generate_company_spec, spec_to_files, _build_memory_files

    def _emit(msg: str) -> None:
        if on_progress:
            on_progress({"type": "step", "message": msg})

    # Validate name
    import re
    if not re.fullmatch(r"^[a-z0-9_]{3,32}$", name):
        raise ValidationError("name", f"must match pattern '^[a-z0-9_]{{3,32}}$' (got '{name}')")

    company_dir = Path(output_dir) / name
    if company_dir.exists():
        raise CollisionError(name)

    # Get LLM
    if llm is None:
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not set. Add it to .env or set the environment variable.")
        from factory.llm.anthropic_client import AnthropicLLMClient
        llm = AnthropicLLMClient()

    _emit(f"Asking Claude to design your company...")

    spec = generate_company_spec(
        description=description,
        name=name,
        agent_count=agent_count,
        work_style=work_style,
        risk_level=risk_level,
        llm=llm,
    )

    agents_list = spec.get("agents", [])
    steps_list  = spec.get("workflow_steps", [])
    _emit(f"Generated: {len(agents_list)} agents, {len(steps_list) - 1} workflow steps")

    rendered = spec_to_files(spec, name, risk_level, work_style)
    mem_files = _build_memory_files(spec)

    _emit("Writing project files...")

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp) / name
        tmp.mkdir()

        for filename, content in rendered.items():
            (tmp / filename).write_text(content, encoding="utf-8")

        # Init memory
        mem_dir = tmp / "memory"
        mem_dir.mkdir()
        for fname in mem_files:
            header = f"# {fname.replace('.md','').replace('_',' ').title()}"
            (mem_dir / fname).write_text(header + "\n", encoding="utf-8")
        (mem_dir / "briefings").mkdir()

        (tmp / "logs").mkdir()

        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = {
            "name": name,
            "template_id": "generated",
            "company_type": spec.get("company_type", "ai_company"),
            "template_version": 1.0,
            "created_at": created_at,
            "inputs": {
                "name": name,
                "risk_level": risk_level,
                "work_style": work_style,
                "agent_count": agent_count,
                "description": description,
                "execution_mode": "paper",
            },
            "generated_spec": {
                "agents":         [a["id"] for a in agents_list],
                "company_type":   spec.get("company_type"),
                "description":    spec.get("description"),
            },
        }
        (tmp / ".manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        _write_standalone_files(tmp, name, spec.get("company_type", "generated"))

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), str(company_dir))

    log.info("Created AI-generated company '%s' (%s) at %s", name, spec.get("company_type"), company_dir)

    if register:
        from factory.registry import registry, CompanyRecord
        registry.add(CompanyRecord(
            name=name,
            template=spec.get("company_type", "generated"),
            path=str(company_dir.resolve()),
            created_at=created_at,
        ))

    return CompanyInstance(name=name, path=company_dir, manifest=manifest)


def _init_memory(company_tmp: Path, template: Template) -> None:
    schema_path = template.root / "memory_schema.yaml"
    mem_dir = company_tmp / "memory"
    mem_dir.mkdir()
    if not schema_path.exists():
        return
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    for file_spec in schema.get("files", []):
        header = file_spec.get("header", "")
        (mem_dir / file_spec["name"]).write_text(header + "\n", encoding="utf-8")
    for dir_name in schema.get("dirs", []):
        (mem_dir / dir_name).mkdir(parents=True, exist_ok=True)


def _write_standalone_files(project_dir: Path, name: str, template_id: str) -> None:
    """Write self-contained runner files + bundle engine into the generated project."""

    (project_dir / "run_cycle.py").write_text(_RUN_CYCLE_PY.format(name=name), encoding="utf-8")
    (project_dir / "start.py").write_text(_START_PY.format(name=name), encoding="utf-8")
    (project_dir / "pyproject.toml").write_text(_PYPROJECT.format(name=name), encoding="utf-8")
    (project_dir / "requirements.txt").write_text(_REQUIREMENTS, encoding="utf-8")
    (project_dir / ".env.template").write_text(_ENV_TEMPLATE.format(name=name), encoding="utf-8")
    (project_dir / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
    (project_dir / "README.md").write_text(_README.format(name=name, template=template_id), encoding="utf-8")

    # Bundle factory engine so project runs without factory installed
    _bundle_engine(project_dir)
    # Bundle company portal (CEO → Secretary → team UI)
    _bundle_portal(project_dir)


def _bundle_engine(project_dir: Path) -> None:
    """Copy factory engine into project_dir/engine/ and rewrite imports.

    After bundling, the project is fully standalone:
      python run_cycle.py --mock   # works without factory installed
    """
    factory_src = Path(__file__).parent   # .../factory/
    engine_dst  = project_dir / "engine"
    engine_dst.mkdir(exist_ok=True)

    bundle = [
        ("errors.py",               "errors.py"),
        ("memory.py",               "memory.py"),
        ("autonomy.py",             "autonomy.py"),
        ("brief.py",                "brief.py"),
        ("run.py",                  "run.py"),
        ("llm/__init__.py",         "llm/__init__.py"),
        ("llm/base.py",             "llm/base.py"),
        ("llm/mock.py",             "llm/mock.py"),
        ("llm/anthropic_client.py", "llm/anthropic_client.py"),
        ("llm/budget_guard.py",     "llm/budget_guard.py"),
        ("agents/__init__.py",      "agents/__init__.py"),
        ("agents/base.py",          "agents/base.py"),
        ("agents/generic.py",       "agents/generic.py"),
        ("agents/analyst.py",       "agents/analyst.py"),
        ("agents/risk.py",          "agents/risk.py"),
        ("agents/ceo.py",           "agents/ceo.py"),
    ]

    # Lines containing these patterns are removed (factory-only modules)
    _DROP = [
        "from engine.registry import",
        "from engine.templates import",
        "from engine.create import",
        "from engine.generator import",
        "from engine.cmd_",
        "from engine.config import COMPANIES_DIR",
        "from engine.config import TEMPLATES_DIR",
        "from engine.config import _ROOT",
    ]

    for src_rel, dst_rel in bundle:
        src = factory_src / src_rel
        if not src.exists():
            continue
        dst = engine_dst / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)

        content = src.read_text(encoding="utf-8")
        # Rewrite factory.* → engine.*
        content = content.replace("from factory.", "from engine.")
        content = content.replace("import factory.", "import engine.")
        # Drop lines that reference factory-only modules
        lines = [l for l in content.splitlines(keepends=True)
                 if not any(pat in l for pat in _DROP)]
        dst.write_text("".join(lines), encoding="utf-8")
        log.debug("bundled engine/%s", dst_rel)

    # engine package init
    (engine_dst / "__init__.py").write_text(
        '"""Bundled AI Company Engine — do not edit manually."""\n',
        encoding="utf-8",
    )
    # Lightweight config (no factory-specific global paths)
    (engine_dst / "config.py").write_text(_ENGINE_CONFIG, encoding="utf-8")
    log.info("Bundled engine into %s/engine/", project_dir.name)


def _bundle_portal(project_dir: Path) -> None:
    """Copy the company portal template into project_dir/portal/.

    Portal provides:
    - CEO → Secretary chat (WebSocket)
    - Team view (agents.yaml)
    - Task management (task_queue.md)
    - Daily briefings viewer
    - Cycle trigger
    """
    portal_src = Path(__file__).parent.parent / "templates" / "_portal"
    portal_dst = project_dir / "portal"

    if not portal_src.exists():
        log.warning("Portal template not found at %s — skipping", portal_src)
        return

    if portal_dst.exists():
        shutil.rmtree(portal_dst)

    shutil.copytree(str(portal_src), str(portal_dst))

    # Also copy sprite assets if available
    sprites_src = Path(__file__).parent.parent / "api" / "static" / "sprites"
    sprites_dst = portal_dst / "static" / "sprites"
    if sprites_src.exists():
        sprites_dst.mkdir(parents=True, exist_ok=True)
        for f in sprites_src.glob("[0-9]*.png"):
            shutil.copy2(str(f), str(sprites_dst / f.name))

    log.info("Bundled portal into %s/portal/", project_dir.name)


# ── Standalone file templates ────────────────────────────────────

_ENGINE_CONFIG = '''\
"""Standalone engine config — no factory dependencies."""
import os
import logging
from pathlib import Path


def setup_logging(level: str | None = None) -> None:
    level = level or os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(name)s] %(message)s",
    )


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


_load_dotenv()
'''

_REQUIREMENTS = '''\
pyyaml>=6.0
filelock>=3.13
anthropic>=0.40.0
python-dotenv>=1.0
fastapi>=0.115
uvicorn[standard]>=0.30
python-multipart>=0.0.9
'''

_RUN_CYCLE_PY = '''\
#!/usr/bin/env python3
"""Daily cycle runner for {name}.

No factory installation needed — engine is bundled in engine/.

Usage:
    python run_cycle.py                   # real Claude API (set ANTHROPIC_API_KEY in .env)
    python run_cycle.py --mock            # offline, free, no API key needed
    python run_cycle.py --date 2026-06-01
"""
import sys
import argparse
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))   # makes engine/ importable

from engine.run import run_cycle        # noqa: E402
from engine.config import setup_logging  # noqa: E402


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Run daily cycle for {name}")
    parser.add_argument("--date", default=None, help="Date YYYY-MM-DD (default: today)")
    parser.add_argument("--mock", action="store_true", help="Offline mock LLM — no API cost")
    args = parser.parse_args()

    llm = None
    if args.mock:
        from engine.llm.mock import MockLLMClient
        llm = MockLLMClient()

    result = run_cycle(
        company_name=HERE.name,
        companies_dir=HERE.parent,
        date=args.date,
        llm=llm,
    )
    print(f"[OK] Cycle complete for {{result.company!r}} on {{result.date}}")


if __name__ == "__main__":
    main()
'''

_START_PY = '''\
#!/usr/bin/env python3
"""Start the company portal for {name}.

Usage:
    python start.py
Open:
    http://localhost:8001
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import uvicorn

if __name__ == "__main__":
    print("[{name}] Portal  ->  http://localhost:8001")
    print("Press Ctrl+C to stop")
    print()
    uvicorn.run("portal.app:app", host="0.0.0.0", port=8001, reload=False)
'''

_PYPROJECT = '''\
[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.12"
description = "AI Company — generated by AI Company Factory"
dependencies = [
    "pyyaml>=6.0",
    "filelock>=3.13",
    "anthropic>=0.40.0",
    "python-dotenv>=1.0",
]
'''

_ENV_TEMPLATE = '''\
# {name} — Environment Variables
# Copy this file to .env and fill in your values.

ANTHROPIC_API_KEY=sk-ant-paste-your-key-here

# Optional
LOG_LEVEL=INFO
DAILY_RUN_TIME=09:00
'''

_GITIGNORE = '''\
.env
*.log
__pycache__/
*.pyc
.venv/
.pytest_cache/
'''

_README = '''\
# {name}

AI Company — Template: `{template}`

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment (add your API key)
cp .env.template .env

# 3. Run a cycle (offline test — no API key needed)
python run_cycle.py --mock

# 4. Run with real Claude AI
python run_cycle.py
```

No factory installation required. Everything is bundled in `engine/`.

## Files

| File/Folder | Purpose |
|---|---|
| `run_cycle.py` | Run one daily cycle |
| `company.yaml` | Company config + budget |
| `agents.yaml` | Agent roster + roles |
| `workflow.yaml` | Daily cycle steps |
| `constitution.md` | Company values + rules |
| `memory/` | Company knowledge (append-only) |
| `memory/briefings/` | Daily briefs |
| `engine/` | Bundled AI engine (do not edit) |
'''


# ── CLI ──────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    from factory.config import setup_logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Create a standalone AI company project")
    parser.add_argument("--template",         required=True)
    parser.add_argument("--name",             required=True)
    parser.add_argument("--risk-level",       default="low", choices=["low", "medium", "high"])
    parser.add_argument("--initial-capital",  type=float, default=0)
    parser.add_argument("--output-dir",       required=True,
                        help="Directory where the company project will be created")
    args = parser.parse_args(argv)

    inputs = {
        "name": args.name,
        "risk_level": args.risk_level,
        "initial_capital": args.initial_capital,
    }
    try:
        instance = create(args.template, inputs, output_dir=Path(args.output_dir))
        print(f"[OK] Created: {instance.path}")
        return 0
    except ValidationError as e:
        print(f"[ERROR] Validation: {e}")
        return 1
    except CollisionError as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
