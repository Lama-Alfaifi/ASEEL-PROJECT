from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.main import app as aseel_api

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

app = FastAPI(title="ASEEL")

# API under /api
app.mount("/api", aseel_api)

# React frontend
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
else:

    @app.get("/")
    def missing_build():
        return {
            "message": "Frontend not built. Run npm run build in aseel-frontend."
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )