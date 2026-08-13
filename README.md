# SpecForge

SpecForge V2 is a deterministic requirements compiler with an agentic implementation backend, demonstrated with a small Calendar application. It resolves and consolidates independently versioned requirements, creates a bounded work order for Codex, verifies the result deterministically, and records traceable evidence.

## Quick start

Requirements: Python 3.10+ (or `uv`), Node 24+ for the frontend, and optionally Docker.

```bash
uv sync --extra dev
uv run specforge resolve products/calendar
uv run specforge explain SEC-001 --product products/calendar
uv run specforge explain SEC-001 --product products/calendar --target operation:read_event
uv run specforge explain SEC-001 --product products/calendar --group-by resource
uv run specforge plan products/calendar
uv run specforge implement products/calendar --agent codex --dry-run
uv run specforge validate products/calendar
uv run specforge evidence products/calendar
uv run specforge report products/calendar
```

Start the agent-managed application:

```bash
docker compose up --build
```

Then open `http://localhost:5173`. The demo API uses fixed local tokens `demo-token-alice` and `demo-token-bob`; this authentication mechanism is deliberately not production-ready.

Without Docker:

```bash
$env:PYTHONPATH="generated/calendar/app/backend"
uv run uvicorn calendar_app:app --port 8000
```

In another terminal:

```bash
cd generated/calendar/app/frontend
npm install
npm run dev
```

## Deterministic artifacts

`resolve` writes canonical JSON below `generated/calendar/`. V2 contains no templates or template engine; structured compiler artifacts use programmatic serialization and application code is agent-managed. Runtime timestamps exist only in evidence and run records. Knowledge packages are pinned by version and content hash. Reports cover only listed formalized requirements for the recorded revision and make no general legal or regulatory compliance claim.

Architecture is documented using [arc42 and C4](docs/architecture/arc42.md). The normative specification is [SPEC_V2.md](plan/SPEC_V2.md), with the [V2 acceptance matrix](docs/acceptance-v2.md) linking its criteria to executable evidence.

How Knowledge packages are structured and how the compiler turns them into
facts, requirements, patterns, and evidence is described in
[Knowledge in SpecForge](docs/knowledge.md).
