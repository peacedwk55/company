from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

from api.routes.companies import router as companies_router
from api.routes.cycles import router as cycles_router
from api.routes.generator import router as generator_router

app = FastAPI(title="AI Company Factory", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"

app.include_router(companies_router)
app.include_router(cycles_router)
app.include_router(generator_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/company/{name}")
async def company_dashboard(name: str):
    """Serve the pixel bot dashboard for a specific company."""
    from factory.registry import registry
    from fastapi.responses import HTMLResponse
    if not registry.get(name):
        return HTMLResponse(
            f"<h2 style='font-family:monospace'>Company '{name}' not found in registry.</h2>"
            f"<p><a href='/'>← Back to Factory</a></p>",
            status_code=404,
        )
    return FileResponse(str(STATIC_DIR / "company.html"))
