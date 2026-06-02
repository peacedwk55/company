import asyncio
import concurrent.futures
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from factory.registry import registry
from factory.run import run_cycle

router = APIRouter()


@router.websocket("/ws/{company_name}/run")
async def websocket_run_cycle(websocket: WebSocket, company_name: str):
    """Run one cycle and stream progress via WebSocket.

    Looks up the company path from registry.

    Event types:
      {"type": "agent",  "agent": "analyst", "summary": "..."}
      {"type": "brief",  "content": "# Daily Brief..."}
      {"type": "done",   "date": "2026-06-01"}
      {"type": "error",  "message": "..."}
    """
    await websocket.accept()

    # Resolve path from registry
    record = registry.get(company_name)
    if record is None:
        await websocket.send_json({"type": "error", "message": f"'{company_name}' not found in registry"})
        await websocket.close()
        return

    company_dir = Path(record.path)
    companies_dir = company_dir.parent

    loop = asyncio.get_event_loop()
    msg_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(data: dict) -> None:
        loop.call_soon_threadsafe(msg_queue.put_nowait, data)

    def run_in_thread() -> None:
        try:
            result = run_cycle(
                company_name,
                companies_dir=companies_dir,
                on_progress=on_progress,
            )
            brief_content = ""
            if result.brief_path.exists():
                brief_content = result.brief_path.read_text(encoding="utf-8")
            loop.call_soon_threadsafe(msg_queue.put_nowait, {"type": "brief", "content": brief_content})
            loop.call_soon_threadsafe(msg_queue.put_nowait, {"type": "done", "date": result.date})
        except Exception as exc:
            loop.call_soon_threadsafe(msg_queue.put_nowait, {"type": "error", "message": str(exc)})

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = loop.run_in_executor(executor, run_in_thread)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(msg_queue.get(), timeout=60.0)
                await websocket.send_json(msg)
                if msg.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        await future
        executor.shutdown(wait=False)
