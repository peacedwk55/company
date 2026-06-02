import json
import shutil
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from factory.config import TEMPLATES_DIR
from factory.create import create
from factory.errors import ValidationError, CollisionError
from factory.memory import MemoryManager
from factory.registry import registry

router = APIRouter(prefix="/api")


def _role_to_emoji(role: str, model_tier: str) -> str:
    """Map agent role + model_tier to a display emoji for the pixel dashboard."""
    r = role.lower()
    if model_tier == "critical" or any(k in r for k in ("ceo", "chief", "director", "head", "lead")):
        return "👑"
    if any(k in r for k in ("analyst", "research", "data", "intelligence", "scientist")):
        return "📊"
    if any(k in r for k in ("risk", "security", "compliance", "protection", "guard")):
        return "🛡️"
    if any(k in r for k in ("write", "writer", "content", "creative", "editor", "copy")):
        return "✍️"
    if any(k in r for k in ("market", "sales", "growth", "revenue", "business development")):
        return "📈"
    if any(k in r for k in ("develop", "engineer", "code", "tech", "software", "backend", "frontend")):
        return "💻"
    if any(k in r for k in ("portfolio", "finance", "trading", "invest", "fund", "quant")):
        return "💰"
    if any(k in r for k in ("manage", "project", "coordinator", "scrum", "product", "pm")):
        return "📋"
    if any(k in r for k in ("support", "customer", "service", "help", "success")):
        return "🎧"
    if any(k in r for k in ("design", "ux", "ui", "visual", "graphic")):
        return "🎨"
    if any(k in r for k in ("track", "monitor", "report", "performance", "metric")):
        return "📡"
    return "🤖"


# ------------------------------------------------------------------
# List companies from registry
# ------------------------------------------------------------------
@router.get("/companies")
async def list_companies():
    records = registry.all()
    companies = []
    for r in sorted(records, key=lambda x: x.name):
        company_dir = Path(r.path)
        briefings_dir = company_dir / "memory" / "briefings"
        briefs = sorted(briefings_dir.glob("*.md")) if briefings_dir.exists() else []
        companies.append({
            "name":       r.name,
            "template":   r.template,
            "path":       r.path,
            "created_at": r.created_at[:10],
            "last_run":   briefs[-1].stem if briefs else None,
            "briefs_count": len(briefs),
            "exists":     company_dir.exists(),
        })
    return {"companies": companies}


# ------------------------------------------------------------------
# Agent roster for pixel dashboard
# NOTE: must be registered BEFORE /companies/{name} to avoid wildcard capture
# ------------------------------------------------------------------
@router.get("/companies/{name}/agents")
async def get_company_agents(name: str):
    """Return agent list with emoji mappings for the pixel bot dashboard."""
    record = registry.get(name)
    if not record:
        raise HTTPException(404, f"'{name}' not found in registry")

    agents_path = Path(record.path) / "agents.yaml"
    if not agents_path.exists():
        return {"agents": []}

    raw = yaml.safe_load(agents_path.read_text(encoding="utf-8")) or {}
    agents = []
    for a in raw.get("agents", []):
        agents.append({
            "id":              a["id"],
            "role":            a["role"],
            "model_tier":      a.get("model_tier", "reasoning"),
            "emoji":           _role_to_emoji(a["role"], a.get("model_tier", "")),
            "responsibilities": a.get("responsibilities", []),
        })
    return {"agents": agents}


# ------------------------------------------------------------------
# Company status
# ------------------------------------------------------------------
@router.get("/companies/{name}")
async def get_company(name: str):
    record = registry.get(name)
    if not record:
        raise HTTPException(404, f"'{name}' not found in registry")

    company_dir = Path(record.path)
    if not company_dir.exists():
        raise HTTPException(404, f"Project folder missing: {record.path}")

    manifest_path = company_dir / ".manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    mm = MemoryManager(company_dir)
    memory = {
        "observations": len(mm.entries("observations.md")),
        "decisions":    len(mm.entries("decisions.md")),
        "risk_log":     len(mm.entries("risk_log.md")),
        "hypotheses":   len(mm.entries("hypotheses.md")),
        "open_tasks":   len(mm.open_tasks()),
    }

    briefings_dir = company_dir / "memory" / "briefings"
    briefs = sorted(briefings_dir.glob("*.md")) if briefings_dir.exists() else []

    return {
        "name":         name,
        "template":     record.template,
        "path":         record.path,
        "created_at":   record.created_at[:10],
        "mode":         manifest.get("inputs", {}).get("execution_mode", "paper"),
        "risk_level":   manifest.get("inputs", {}).get("risk_level", "low"),
        "memory":       memory,
        "briefs_count": len(briefs),
        "last_run":     briefs[-1].stem if briefs else None,
    }


# ------------------------------------------------------------------
# Last brief
# ------------------------------------------------------------------
@router.get("/companies/{name}/brief")
async def get_last_brief(name: str):
    record = registry.get(name)
    if not record:
        raise HTTPException(404, f"'{name}' not found in registry")
    briefings_dir = Path(record.path) / "memory" / "briefings"
    briefs = sorted(briefings_dir.glob("*.md")) if briefings_dir.exists() else []
    if not briefs:
        return {"date": None, "content": ""}
    last = briefs[-1]
    return {"date": last.stem, "content": last.read_text(encoding="utf-8")}


# ------------------------------------------------------------------
# Create company
# ------------------------------------------------------------------
class CreateRequest(BaseModel):
    template: str
    name: str
    risk_level: str = "low"
    initial_capital: float = 0
    output_dir: str        # user-specified path


@router.post("/companies", status_code=201)
async def create_company(req: CreateRequest):
    try:
        instance = create(
            req.template,
            {"name": req.name, "risk_level": req.risk_level, "initial_capital": req.initial_capital},
            output_dir=Path(req.output_dir),
        )
        return {"name": instance.name, "path": str(instance.path)}
    except ValidationError as e:
        raise HTTPException(400, str(e))
    except CollisionError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ------------------------------------------------------------------
# Delete company
# ------------------------------------------------------------------
@router.delete("/companies/{name}")
async def delete_company(name: str):
    record = registry.get(name)
    if not record:
        raise HTTPException(404, f"'{name}' not found in registry")
    company_dir = Path(record.path)
    if company_dir.exists():
        shutil.rmtree(company_dir)
    registry.remove(name)
    return {"deleted": name}


# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------
@router.get("/templates")
async def list_templates():
    if not TEMPLATES_DIR.exists():
        return {"templates": []}
    templates = []
    for d in TEMPLATES_DIR.iterdir():
        if not d.is_dir():
            continue
        meta_path = d / "template.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        templates.append({
            "id":          meta.get("id"),
            "name":        meta.get("name"),
            "description": meta.get("description", ""),
        })
    return {"templates": templates}
