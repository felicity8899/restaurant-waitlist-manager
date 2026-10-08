import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException

DB_PATH = os.getenv("INCIDENT_DB_PATH", "data/incidents.db")
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://tempo:3200")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("incident-response")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                alert_name TEXT NOT NULL,
                status TEXT NOT NULL,
                affected_endpoint TEXT,
                alert_payload TEXT NOT NULL,
                logs TEXT,
                traces TEXT,
                created_at TEXT NOT NULL
            )
        """)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Incident Response Service", lifespan=lifespan)

async def fetch_loki_logs(endpoint_filter: str = None) -> dict:
    queries = []
    if endpoint_filter:
        queries.extend([
            f'{{exporter="OTLP"}} |= "{endpoint_filter}"',
            f'{{service_name="unknown_service"}} |= "{endpoint_filter}"',
            f'{{job="default"}} |= "{endpoint_filter}"',
            f'{{}} |= "{endpoint_filter}"'
        ])
    else:
        queries.extend([
            '{exporter="OTLP"}',
            '{service_name="unknown_service"}',
            '{job="default"}',
            '{}'
        ])

    async with httpx.AsyncClient() as client:
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=15)
        params = {
            "start": int(start_time.timestamp() * 1e9),
            "end": int(now.timestamp() * 1e9),
            "limit": 100
        }
        
        for q in queries:
            params["query"] = q
            try:
                logger.info("Attempting Loki query: %s", q)
                response = await client.get(f"{LOKI_URL}/loki/api/v1/query_range", params=params, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    streams = data.get("data", {}).get("result", [])
                    if streams:
                        logger.info("Loki query succeeded with %d streams for query: %s", len(streams), q)
                        return data
            except Exception as e:
                logger.warning("Query failed (%s): %s", q, e)
                
        try:
            label_response = await client.get(f"{LOKI_URL}/loki/api/v1/labels", timeout=3.0)
            if label_response.status_code == 200:
                logger.info("Available Loki labels: %s", label_response.json().get("data", []))
        except Exception:
            pass
            
        return {"status": "no_logs_found_or_error"}

async def fetch_tempo_traces(endpoint_filter: str = None) -> list:
    async with httpx.AsyncClient() as client:
        detailed_traces = []
        try:
            params = {"limit": 10}
            if endpoint_filter:
                params["tags"] = f'http.route="{endpoint_filter}"'
                logger.info("Attempting Tempo search with tags: %s", params["tags"])
                
                response = await client.get(f"{TEMPO_URL}/api/search", params=params, timeout=5.0)
                if response.status_code == 200:
                    traces = response.json().get("traces", [])
                    if traces:
                        logger.info("Tempo trace search with tags succeeded. Found %d traces.", len(traces))
                        detailed_traces = await get_trace_details(client, traces)
                        if detailed_traces:
                            return detailed_traces

            logger.info("Tempo searching all recent traces")
            fallback_response = await client.get(f"{TEMPO_URL}/api/search", params={"limit": 10}, timeout=5.0)
            if fallback_response.status_code == 200:
                traces = fallback_response.json().get("traces", [])
                detailed_traces = await get_trace_details(client, traces)
                
            return detailed_traces
        except Exception as e:
            logger.error("Failed to fetch traces from Tempo: %s", e)
            return [{"error": str(e)}]

async def get_trace_details(client: httpx.AsyncClient, traces: list) -> list:
    details = []
    for t in traces:
        trace_id = t.get("traceID")
        if trace_id:
            try:
                detail_resp = await client.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=5.0)
                if detail_resp.status_code == 200:
                    details.append(detail_resp.json())
                else:
                    details.append(t)
            except Exception as e:
                logger.warning("Failed to fetch trace details for %s: %s", trace_id, e)
                details.append(t)
    return details

@app.post("/alerts")
async def receive_alerts(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse request JSON: %s", e)
        raise HTTPException(400, "Invalid JSON payload")

    logger.info("Received alert payload: %s", json.dumps(payload, indent=2))
    
    alerts_list = payload.get("alerts", [])
    if not alerts_list:
        alerts_list = [payload]
        
    saved_incidents = []
    for alert in alerts_list:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        alert_name = labels.get("alertname") or annotations.get("summary") or "Unnamed Alert"
        status = alert.get("status") or payload.get("status") or "firing"
        
        affected_endpoint = (
            labels.get("route") or
            labels.get("endpoint") or
            labels.get("http_route") or
            annotations.get("endpoint") or
            annotations.get("route")
        )
        
        if not affected_endpoint:
            description = annotations.get("description", "")
            summary = annotations.get("summary", "")
            for text in (description, summary):
                if "/api/" in text:
                    parts = text.split()
                    for p in parts:
                        if p.startswith("/api/"):
                            affected_endpoint = p.rstrip(".,;:)")
                            break
        
        logger.info("Fetching telemetry for endpoint: %s", affected_endpoint)
        logs = await fetch_loki_logs(affected_endpoint)
        traces = await fetch_tempo_traces(affected_endpoint)
        
        incident_id = alert.get("fingerprint") or f"inc-{int(datetime.now().timestamp())}-{len(saved_incidents)}"
        created_at = datetime.now(timezone.utc).isoformat()
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO incidents (id, alert_name, status, affected_endpoint, alert_payload, logs, traces, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        incident_id,
                        alert_name,
                        status,
                        affected_endpoint,
                        json.dumps(alert),
                        json.dumps(logs),
                        json.dumps(traces),
                        created_at
                    )
                )
            logger.info("Successfully saved incident %s to database", incident_id)
            saved_incidents.append({
                "incident_id": incident_id,
                "alert_name": alert_name,
                "status": status,
                "affected_endpoint": affected_endpoint
            })
        except Exception as e:
            logger.error("Failed to save incident to database: %s", e)
            
    return {
        "status": "processed",
        "processed_count": len(saved_incidents),
        "incidents": saved_incidents
    }

@app.get("/incidents")
def list_incidents():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, alert_name, status, affected_endpoint, created_at FROM incidents ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Incident not found")
            res = dict(row)
            res["alert_payload"] = json.loads(res["alert_payload"])
            if res["logs"]:
                res["logs"] = json.loads(res["logs"])
            if res["traces"]:
                res["traces"] = json.loads(res["traces"])
            return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/healthz")
def healthz():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, f"Unhealthy: {e}")
