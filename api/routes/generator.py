"""WebSocket route for AI company generation.

/ws/factory/generate streams progress while Claude designs and creates the company.

Events sent to client:
  {"type": "step",  "message": "Asking Claude..."}
  {"type": "spec",  "agents": [...], "company_type": "..."}  ← preview before writing files
  {"type": "step",  "message": "Writing project files..."}
  {"type": "done",  "name": "...", "path": "...", "company_type": "...", "agents": [...]}
  {"type": "error", "message": "..."}
"""
import asyncio
import concurrent.futures
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from factory.create import create_from_description
from factory.errors import ValidationError, CollisionError

router = APIRouter()


@router.websocket("/ws/factory/generate")
async def websocket_generate(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except asyncio.TimeoutError:
        await websocket.send_json({"type": "error", "message": "No data received"})
        return

    description = data.get("description", "").strip()
    name        = data.get("name", "").strip().lower()
    output_dir  = data.get("output_dir", "").strip()
    agent_count = int(data.get("agent_count", 3))
    work_style  = data.get("work_style", "balanced")
    risk_level  = data.get("risk_level", "low")

    if not description:
        await websocket.send_json({"type": "error", "message": "Description is required"}); return
    if not name:
        await websocket.send_json({"type": "error", "message": "Name is required"}); return
    if not output_dir:
        await websocket.send_json({"type": "error", "message": "Output directory is required"}); return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        await websocket.send_json({"type": "error", "message": "ANTHROPIC_API_KEY not set in .env"}); return

    loop = asyncio.get_event_loop()
    msg_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(evt: dict) -> None:
        loop.call_soon_threadsafe(msg_queue.put_nowait, evt)

    def run_in_thread() -> None:
        from pathlib import Path
        try:
            instance = create_from_description(
                description=description,
                name=name,
                output_dir=Path(output_dir),
                agent_count=agent_count,
                work_style=work_style,
                risk_level=risk_level,
                on_progress=on_progress,
            )
            manifest   = instance.manifest
            spec_info  = manifest.get("generated_spec", {})
            loop.call_soon_threadsafe(msg_queue.put_nowait, {
                "type":         "done",
                "name":         instance.name,
                "path":         str(instance.path),
                "company_type": spec_info.get("company_type", ""),
                "description":  spec_info.get("description", ""),
                "agents":       spec_info.get("agents", []),
            })
        except (ValidationError, CollisionError) as e:
            loop.call_soon_threadsafe(msg_queue.put_nowait, {"type": "error", "message": str(e)})
        except Exception as e:
            loop.call_soon_threadsafe(msg_queue.put_nowait, {"type": "error", "message": str(e)})

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future   = loop.run_in_executor(executor, run_in_thread)

    try:
        while True:
            try:
                evt = await asyncio.wait_for(msg_queue.get(), timeout=120.0)
                await websocket.send_json(evt)
                if evt.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "step", "message": "Still working..."})
    except WebSocketDisconnect:
        pass
    finally:
        await future
        executor.shutdown(wait=False)
