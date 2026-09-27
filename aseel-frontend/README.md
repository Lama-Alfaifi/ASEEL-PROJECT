# ASEEL frontend

A complete web product for ASEEL (أصيل) — Saudi cultural etiquette and heritage guidance — built on the **existing FastAPI API**. The agents, workflow and `main.py` are untouched.

Stack: React 18 + TypeScript + Vite. No UI framework; the visual identity is hand-built CSS. Fonts are bundled (no CDN). English and Arabic (full RTL), light and dark themes.

## Quick start

Put this folder inside your ASEEL project (next to `main.py`) and name it `frontend/`.

**Development** (hot reload; Vite proxies `/api` to FastAPI, so no CORS setup is needed):

```bash
# terminal 1 — your existing backend
uvicorn main:app --port 8000

# terminal 2
cd frontend
npm install
npm run dev            # http://localhost:5173
```

**Production, one process** (serves the built UI and mounts your API at `/api`):

```bash
cd frontend && npm install && npm run build && cd ..
python frontend/serve_ui.py       # http://127.0.0.1:8000
```

`serve_ui.py` only imports `app` from `main.py`; it does not edit it. A pre-built `dist/` is included so this works before you run `npm`.

**No OpenAI key yet?** `scripts/mock_api.py` mimics `POST /chat` with clearly-labelled placeholder text so you can work on the UI:

```bash
uvicorn scripts.mock_api:app --port 8000
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_TARGET` | `http://127.0.0.1:8000` | Where the dev/preview server forwards `/api` |
| `VITE_API_BASE` | `/api` | Base URL used by the browser (also editable in Settings) |

A full URL such as `http://127.0.0.1:8000` in Settings only works if the backend allows CORS (it currently doesn't).

## What's in the product

| Area | What it does |
|---|---|
| **Home** | Hero search, region map, topic starters, and a plain-language explanation of the four-agent pipeline |
| **Ask** | Multi-thread chat. Region hint chips, "ask next" suggestions, cancel/retry, conversation context sent like `app.py` did (last 5 messages) |
| **Answer card** | Status, a 10-segment confidence bar with the 0.5 validation threshold marked, regions the evidence came from, expandable evidence, save/copy |
| **Explore** | Interactive map (real province boundaries, each region filled with its own woven motif), 13 city pins, 9 topics per region, cached "region cards", *Surprise me* |
| **Plan a visit** | Occasion + role + region + focus builds one question and returns a printable/downloadable etiquette brief |
| **Source explorer** | Every knowledge-base entry seen so far: search, region/category filters, sort by relevance/recency/usage, coverage bar, "used in N answers" |
| **Saved** | Bookmark answers and sources; add notes and tags; search; export Markdown |
| **Smart search** | `Ctrl/⌘ + K`: jump to pages, regions, cities, topics, chats, saved items and sources, or type a question and ask it |
| **Settings** | Language, theme, API address with connection test, data export/clear |

## How it uses the API

Only the two existing endpoints:

- `GET /` → health pill in the header
- `POST /chat` `{ message, conversation_context }` → `{ answer, status, confidence_score, sources[] }`

Everything else is derived on the client:

- **Source explorer** is built from the `sources` of answers you've received. The API has no endpoint that lists the whole knowledge base, and the UI says so.
- **Region hint** appends "(in the South region of Saudi Arabia)" to the question, because the backend resolves regions from the text.
- **Topics, cities and briefs** are just *questions* sent to `/chat`. No cultural facts are written in the frontend; every claim you see comes from the API.
- **Pipeline loader** walks the four stages from `graph.py` on an approximate timeline. The API is one blocking request with no per-stage progress, so this is illustrative, not live telemetry.
- The map groups the 13 provinces into ASEEL's five regions for *display* (South: Asir, Jazan, Najran, Al Bahah · North: Tabuk, Northern Borders, Al-Jawf, Hail · East: Eastern Province · West: Makkah, Madinah · Central: Riyadh, Al-Qassim). The grouping lives in `src/data/saudiMap.ts`. Your backend's own region matching still decides which entries are used.

User data (chats, saved items, region cards, settings) lives in the browser's `localStorage` only.

## Project layout

```
src/
  lib/         api client, i18n (en/ar), region + topic metadata, router, utils
  state/       app store (settings, threads, saved, discoveries, source index, API health)
  components/  AnswerCard, SourceCard, SaudiMap, PipelineLoader, CommandPalette, Shell…
  pages/       Home, Ask, Explore, Plan, Sources, Saved, Settings
  styles/      tokens.css (palette, type, radii) · base.css · pages.css
  data/        saudiMap.ts (generated from Natural Earth admin-1, public domain)
scripts/mock_api.py    dev stand-in for the API
serve_ui.py            production wrapper (UI + your API, one origin)
```

To rebrand, edit `src/styles/tokens.css`. To add or rename topics, edit `TOPICS` in `src/lib/regions.ts`. UI strings are in `src/lib/i18n.ts`.

## Notes on the backend (observed, not changed)

- `main.py` has no CORS middleware → handled by the proxy / `serve_ui.py`.
- `ask()` calls `build_workflow()` (graph compile) on every request; caching the compiled graph would trim latency.
- `validation_agent` in `validation.py` is created but never invoked (validation runs deterministically), so it costs nothing at runtime but is dead code.
- Understanding, retrieval and response each use an LLM agent around what are effectively single tool calls, so answers take several seconds. The UI is designed around that wait.
- Any exception inside `ask()` becomes an HTTP 500; the UI shows a retry card for it.
- Optional future endpoints that would unlock richer UI without touching the agents: `GET /regions`, `GET /sources` (KB listing), and a streamed `/chat` with stage events for a real progress indicator.

## Credits

Province boundaries: Natural Earth (public domain). Fonts: IBM Plex Sans Arabic and Reem Kufi (SIL OFL), bundled via Fontsource.
