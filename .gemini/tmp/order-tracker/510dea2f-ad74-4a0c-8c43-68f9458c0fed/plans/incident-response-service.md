# Incident Response Service Implementation Plan

## Objective
Build a new `incident-response` service that receives Grafana webhooks at `POST /alerts` on port `8001`. Upon receiving an alert, it will query Loki (for logs) and Tempo (for traces), and save this information into a SQLite database to help engineers understand the problem.

## Key Files & Context
- `pyproject.toml` & `uv.lock`: Needs update to include `httpx` in main dependencies for making API calls to Loki/Tempo.
- `incident-response/main.py`: The FastAPI application code.
- `incident-response/Dockerfile`: Container definition for the new service.
- `compose.yaml`: Needs to be updated to add the `incident-response` service.

## Implementation Steps

1. **Dependencies:**
   - Move `httpx` from the `[dependency-groups] dev` section to the main `dependencies` in `pyproject.toml`.
   - Run `uv sync` to update `uv.lock`.

2. **Service Application (`incident-response/main.py`):**
   - Initialize a FastAPI application.
   - Create a SQLite database (e.g., at `/data/incidents.db`) and a table to store incident details (e.g., ID, endpoint, logs, traces, timestamp).
   - Add a `POST /alerts` endpoint that:
     - Parses the Grafana alert payload.
     - Extracts relevant labels/annotations (e.g., the affected endpoint or service).
     - Asynchronously fetches recent logs from Loki (`http://loki:3100/loki/api/v1/query_range`).
     - Asynchronously fetches trace data from Tempo (`http://tempo:3200/api/search`).
     - Saves the combined JSON structure into the SQLite database.

3. **Containerization (`incident-response/Dockerfile`):**
   - Create a Dockerfile for the service based on the existing `app` Dockerfile structure.
   - Use `uvicorn` to start the service: `uv run uvicorn incident-response.main:app --host 0.0.0.0 --port 8001`.

4. **Docker Compose (`compose.yaml`):**
   - Add an `incident-response` service.
   - Map port `8001:8001`.
   - Pass environment variables for Loki and Tempo URLs.
   - Define a volume (`incident-data:/data`) to persist the SQLite database.

## Verification & Testing
- Run `docker compose build incident-response` and start the services.
- Send a mock Grafana alert payload to `http://localhost:8001/alerts` using `curl` or a test script.
- Verify that the service queries Loki and Tempo correctly (observing the logs of the service).
- Verify that the SQLite DB stores the alert along with the fetched logs and traces.