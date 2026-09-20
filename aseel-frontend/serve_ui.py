"""
Serve the built frontend AND the existing ASEEL API from one origin.

This file only *imports* your FastAPI app from main.py and mounts it under /api.
main.py, the agents and the workflow are not modified. Because the browser talks to a
single origin, no CORS configuration is needed.

Place this frontend folder inside the ASEEL project root (next to main.py), then:

    cd frontend
    npm install && npm run build
    cd ..
    python frontend/serve_ui.py            # http://127.0.0.1:8000

Environment: ASEEL_UI_HOST (default 127.0.0.1), ASEEL_UI_PORT (default 8000).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # project root, so `main`, `workflow`, `agents` import as usual

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from main import app as aseel_api  # noqa: E402  (your existing FastAPI app, untouched)

DIST = HERE / "dist"

app = FastAPI(title="ASEEL")
app.mount("/api", aseel_api)
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
else:

    @app.get("/")
    def missing_build():
        return {"message": "Frontend not built. Run `npm install && npm run build` in the frontend folder."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("ASEEL_UI_HOST", "127.0.0.1"), port=int(os.getenv("ASEEL_UI_PORT", "8000")))
