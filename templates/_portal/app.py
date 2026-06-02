"""Company Portal — FastAPI backend.

Serves the company portal UI and handles:
- Team info (agents.yaml)
- Tasks (memory/task_queue.md)
- Briefings (memory/briefings/)
- Secretary chat (WebSocket — CEO → Secretary → distribute tasks)
- Cycle trigger (WebSocket — run specific or all agents)
"""
import sys
import json
import logging
import yaml
import re
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

HERE = Path(__file__).parent
ROOT = HERE.parent          # company project root
sys.path.insert(0, str(ROOT))

from engine.memory import MemoryManager  # noqa: E402

log = logging.getLogger(__name__)

app = FastAPI(title="Company Portal")

# ── Helpers ───────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def get_company() -> dict:
    return load_yaml(ROOT / "company.yaml")

def get_agents() -> list[dict]:
    data = load_yaml(ROOT / "agents.yaml")
    return data.get("agents", [])

def get_mm() -> MemoryManager:
    return MemoryManager(ROOT)

# ── REST API ──────────────────────────────────────────────────────

@app.get("/api/company")
async def api_company():
    return get_company()

@app.get("/api/team")
async def api_team():
    agents = get_agents()
    # Assign sprite numbers deterministically
    for i, a in enumerate(agents):
        a["sprite"] = (i % 11) + 1
    return {"agents": agents}

@app.get("/api/tasks")
async def api_tasks():
    mm = get_mm()
    entries = mm.entries("task_queue.md")
    open_tasks   = [e for e in entries if e.kind == "task"   and "Status: Open" in e.body]
    closed_ids   = {e.body.split("→ ")[1].split(":")[0].strip()
                    for e in entries if e.kind == "taskupdate" and "Completed" in e.body}
    active = [t for t in open_tasks if t.id not in closed_ids]
    closed = [t for t in open_tasks if t.id in closed_ids]

    def parse_task(e):
        lines = dict(l.split(": ", 1) for l in e.body.splitlines() if ": " in l)
        return {
            "id":       e.id,
            "title":    lines.get("Title", e.body[:60]),
            "priority": lines.get("Priority", "medium"),
            "assigned": lines.get("Assigned", e.agent),
            "due":      lines.get("Due", ""),
            "ts":       e.ts,
            "status":   "open",
        }

    return {
        "open":   [parse_task(t) for t in active],
        "closed": [parse_task(t) for t in closed[:5]],
    }

class TaskBody(BaseModel):
    title: str
    assigned_to: str = "secretary"
    priority: str = "medium"
    due_date: str | None = None

@app.post("/api/tasks", status_code=201)
async def create_task(body: TaskBody):
    mm = get_mm()
    entry = mm.create_task(
        body.title,
        agent=body.assigned_to,
        priority=body.priority,
        due_date=body.due_date,
    )
    return {"id": entry.id, "title": body.title}

@app.patch("/api/tasks/{task_id}/done")
async def close_task(task_id: str):
    mm = get_mm()
    mm.update_task(task_id, status="Completed", agent="portal")
    return {"closed": task_id}

@app.get("/api/briefings")
async def api_briefings():
    briefings_dir = ROOT / "memory" / "briefings"
    if not briefings_dir.exists():
        return {"briefings": []}
    files = sorted(briefings_dir.glob("*.md"), reverse=True)
    return {"briefings": [f.stem for f in files[:20]]}

@app.get("/api/briefings/{date}")
async def api_briefing(date: str):
    path = ROOT / "memory" / "briefings" / f"{date}.md"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"date": date, "content": path.read_text(encoding="utf-8")}

@app.get("/api/stats")
async def api_stats():
    mm = get_mm()
    return {
        "observations": len(mm.entries("observations.md")),
        "decisions":    len(mm.entries("decisions.md")),
        "risk_log":     len(mm.entries("risk_log.md")),
        "open_tasks":   len(mm.open_tasks()),
        "hypotheses":   len(mm.entries("hypotheses.md")),
        "briefs":       len(list((ROOT / "memory" / "briefings").glob("*.md"))) if (ROOT / "memory" / "briefings").exists() else 0,
    }

@app.get("/api/recent")
async def api_recent():
    """Recent observations + decisions for activity feed."""
    mm = get_mm()
    obs  = mm.entries("observations.md")[-8:]
    decs = mm.entries("decisions.md")[-4:]
    combined = sorted(obs + decs, key=lambda e: e.ts, reverse=True)[:10]
    return {"entries": [{"id": e.id, "agent": e.agent, "kind": e.kind, "body": e.body[:120], "ts": e.ts} for e in combined]}

# ── Secretary WebSocket ───────────────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """CEO → Secretary → distribute tasks to team."""
    await websocket.accept()

    company = get_company()
    company_name = company.get("name", "Company")

    try:
        while True:
            raw = await websocket.receive_json()
            user_msg = raw.get("message", "").strip()
            if not user_msg:
                continue

            agents = get_agents()
            agents_desc = "\n".join(
                f"- {a['id']} ({a['role']}): {', '.join(a.get('responsibilities', [])[:2])}"
                for a in agents
            )

            system_prompt = (
                f"คุณคือเลขาของบริษัท {company_name}\n"
                f"หน้าที่: รับคำสั่งจาก CEO แล้วกระจายงานให้ทีมตามความเหมาะสม\n\n"
                f"ทีมงานปัจจุบัน:\n{agents_desc}\n\n"
                f"เมื่อรับคำสั่งจาก CEO ให้:\n"
                f"1. ตอบรับอย่างกระชับและเป็นมืออาชีพ\n"
                f"2. ระบุว่าจะมอบหมายงานอะไรให้ใคร\n"
                f"3. สร้าง task list ที่ชัดเจน\n\n"
                f"ตอบเป็น JSON ดังนี้เท่านั้น:\n"
                f'{{"response": "ข้อความตอบ CEO", '
                f'"tasks": [{{"title": "ชื่องาน", "assigned_to": "agent_id", "priority": "high|medium|low"}}]}}'
            )

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    from engine.llm.anthropic_client import AnthropicLLMClient
                    llm = AnthropicLLMClient(api_key=api_key)
                    result = llm.complete(
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_msg}],
                        tier="reasoning",
                        max_tokens=1024,
                    )
                    text = result.text
                except Exception as e:
                    text = json.dumps({"response": f"ขออภัยค่ะ เกิดข้อผิดพลาด: {e}", "tasks": []})
            else:
                # Mock mode — deterministic offline response
                text = json.dumps({
                    "response": f"รับทราบค่ะ CEO จะดำเนินการตามที่สั่ง: \"{user_msg}\" ทันที",
                    "tasks": [{"title": user_msg, "assigned_to": agents[0]["id"] if agents else "secretary", "priority": "medium"}]
                })

            # Parse JSON from response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = {"response": text, "tasks": []}
            else:
                data = {"response": text, "tasks": []}

            # Create tasks in memory
            mm = get_mm()
            created = []
            for t in data.get("tasks", []):
                entry = mm.create_task(
                    t.get("title", "งานใหม่"),
                    agent=t.get("assigned_to", "secretary"),
                    priority=t.get("priority", "medium"),
                )
                created.append({"id": entry.id, "title": t.get("title"), "assigned_to": t.get("assigned_to")})

            await websocket.send_json({
                "type":     "secretary",
                "response": data.get("response", ""),
                "tasks":    created,
                "ts":       datetime.now(timezone.utc).strftime("%H:%M"),
            })

    except WebSocketDisconnect:
        pass

# ── Daily cycle WebSocket ─────────────────────────────────────────

@app.websocket("/ws/cycle")
async def ws_cycle(websocket: WebSocket):
    """Trigger a full daily cycle and stream agent progress."""
    import asyncio
    import concurrent.futures

    await websocket.accept()
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()

    def on_progress(evt: dict) -> None:
        loop.call_soon_threadsafe(q.put_nowait, evt)

    def run_thread() -> None:
        try:
            from engine.run import run_cycle
            from engine.config import setup_logging
            setup_logging()
            result = run_cycle(
                company_name=ROOT.name,
                companies_dir=ROOT.parent,
                on_progress=on_progress,
            )
            brief = result.brief_path.read_text(encoding="utf-8") if result.brief_path.exists() else ""
            loop.call_soon_threadsafe(q.put_nowait, {"type": "done", "date": result.date, "brief": brief})
        except Exception as exc:
            loop.call_soon_threadsafe(q.put_nowait, {"type": "error", "message": str(exc)})

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = loop.run_in_executor(executor, run_thread)
    try:
        while True:
            try:
                evt = await asyncio.wait_for(q.get(), timeout=120)
                await websocket.send_json(evt)
                if evt.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        await future
        executor.shutdown(wait=False)

# ── Static files ──────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    from fastapi.responses import Response
    content = (HERE / "static" / "index.html").read_text(encoding="utf-8")
    return Response(content=content, media_type="text/html; charset=utf-8")
