# Objective
Add OpenTelemetry for observability and an in-app webhook to serve as an incident responder. The incident we will simulate is "delayed express orders" (express orders stuck in the 'received' state for an extended period).

# Scope & Impact
- `pyproject.toml`: Add OpenTelemetry dependencies (`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`).
- `app/main.py`: Instrument the FastAPI app with OpenTelemetry to collect traces and metrics. Add a `POST /api/webhook/alerts` endpoint that acts as the incident responder.
- `tests/test_api.py`: Add unit tests for the new webhook to verify it correctly processes "delayed" orders.

# Proposed Solution
1. **Telemetry**: We will configure OpenTelemetry (TracerProvider and MeterProvider) and use `FastAPIInstrumentor` to trace incoming HTTP requests automatically.
2. **Incident Responder Webhook**: A new POST endpoint at `/api/webhook/alerts` will be created. In a real-world setup, an alerting system (e.g., Alertmanager) would call this webhook. When called, this endpoint will identify all "express" orders stuck in the "received" state and automatically update their status to "preparing" or "shipped", effectively "self-healing" the simulated incident.

# Implementation Steps
1. **Add Dependencies**: Update `pyproject.toml` to include `opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-instrumentation-fastapi`.
2. **Instrument App**: Update `app/main.py` to initialize OpenTelemetry providers and call `FastAPIInstrumentor.instrument_app(app)`.
3. **Add Webhook**: Create the `POST /api/webhook/alerts` route in `app/main.py`. This route will query the database for express orders in the "received" state and update them.
4. **Update Tests**: Add a test case in `tests/test_api.py` that seeds a delayed order, calls the webhook, and asserts that the order was successfully progressed.

# Verification & Testing
- Run `uv run pytest` to ensure all tests pass.
- Manually test by running the app in Docker Compose and making a POST request to `/api/webhook/alerts` to ensure it successfully updates the database.
