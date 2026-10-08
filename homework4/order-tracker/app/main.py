import os
import sqlite3
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import CallbackOptions, Observation

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor, ConsoleLogExporter


DB_PATH = Path(os.getenv("ORDER_DB_PATH", "data/orders.db"))
STATUSES = {"received", "preparing", "shipped", "delivered"}


# Setup OpenTelemetry
otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Setup OpenTelemetry Tracing
tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    trace_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
except Exception as e:
    print(f"Failed to setup OTLP trace exporter: {e}")

# Setup OpenTelemetry Metrics
try:
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    metric_exporter = OTLPMetricExporter(endpoint=otel_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(metric_readers=[metric_reader])
except Exception as e:
    print(f"Failed to setup OTLP metric exporter: {e}")
    meter_provider = MeterProvider()

metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("order_tracker_meter")

# Setup OpenTelemetry Logging
logger_provider = LoggerProvider()
set_logger_provider(logger_provider)
try:
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    log_exporter = OTLPLogExporter(endpoint=otel_endpoint, insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
except Exception as e:
    print(f"Failed to setup OTLP log exporter: {e}")

handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger("order-tracker")

# Setup OpenTelemetry Tracer
tracer = trace.get_tracer("order_tracker_tracer")

# Setup Request Counter Metric
order_lookup_requests_counter = meter.create_counter(
    name="order_lookup_requests_total",
    description="Total number of order lookup requests",
    unit="1",
)



def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def get_delayed_orders_count(options: CallbackOptions):
    try:
        with connect() as db:
            now = datetime.now(timezone.utc)
            rows = db.execute(
                "SELECT created_at FROM orders WHERE priority = 'express' AND status NOT IN ('shipped', 'delivered')"
            ).fetchall()
            count = 0
            for row in rows:
                try:
                    placed_at = datetime.fromisoformat(row["created_at"])
                    if now - placed_at > timedelta(minutes=1):
                        count += 1
                except Exception:
                    pass
            return [Observation(count)]
    except Exception:
        return [Observation(0)]


meter.create_observable_gauge(
    name="delayed_express_orders",
    callbacks=[get_delayed_orders_count],
    description="Number of express orders that have been delayed",
)



def init_db():
    with connect() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer TEXT NOT NULL,
                item TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        if db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
            now = datetime.now(timezone.utc)
            previous_month_end = now.replace(day=1) - timedelta(days=1)
            for order in (
                ("standard-1001", "Avery", "Notebook", "standard", "received", now),
                ("express-1002", "Sam", "Headphones", "express", "preparing", previous_month_end),
                ("standard-1003", "Riley", "Water bottle", "standard", "shipped", now),
            ):
                db.execute(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    (*order[:5], order[5].isoformat()),
                )


def as_dict(row):
    return dict(row) if row else None


def order_detail(row):
    order = as_dict(row)
    if order["priority"] == "express":
        placed_at = datetime.fromisoformat(order["created_at"])
        estimated_at = placed_at + timedelta(days=2)
        order["estimated_delivery"] = estimated_at.date().isoformat()
    return order


class NewOrder(BaseModel):
    customer: str = Field(min_length=1, max_length=80)
    item: str = Field(min_length=1, max_length=120)
    priority: str = "standard"


class StatusUpdate(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Order Tracker", lifespan=lifespan)

# Instrument FastAPI App with OpenTelemetry
FastAPIInstrumentor().instrument_app(app)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")


@app.get("/healthz")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/orders")
def list_orders():
    with connect() as db:
        rows = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return [as_dict(row) for row in rows]


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    with tracer.start_as_current_span("order_lookup") as span:
        span.set_attribute("order_id", order_id)
        logger.info("Initiating lookup for order_id: %s", order_id)
        
        with connect() as db:
            row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        
        if row is None:
            logger.warning("Order lookup failed: order_id %s not found", order_id)
            span.set_attribute("http.status_code", 404)
            order_lookup_requests_counter.add(
                1,
                {
                    "route": "/api/orders/{order_id}",
                    "http.status_code": "404",
                }
            )
            raise HTTPException(404, "Order not found")
        
        logger.info("Order lookup succeeded for order_id: %s", order_id)
        span.set_attribute("http.status_code", 200)
        order_lookup_requests_counter.add(
            1,
            {
                "route": "/api/orders/{order_id}",
                "http.status_code": "200",
            }
        )
        return order_detail(row)


@app.post("/api/orders", status_code=201)
def create_order(order: NewOrder):
    if order.priority not in {"standard", "express"}:
        raise HTTPException(422, "Priority must be standard or express")
    order_id = str(uuid4())
    with connect() as db:
        db.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, order.customer, order.item, order.priority, "received",
             datetime.now(timezone.utc).isoformat()),
        )
    return get_order(order_id)


@app.patch("/api/orders/{order_id}")
def update_status(order_id: str, update: StatusUpdate):
    if update.status not in STATUSES:
        raise HTTPException(422, "Invalid status")
    with connect() as db:
        cursor = db.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (update.status, order_id),
        )
    if cursor.rowcount == 0:
        raise HTTPException(404, "Order not found")
    return get_order(order_id)


@app.post("/api/webhook/alerts")
def alert_webhook(payload: dict = None):
    # Incident responder: self-heal delayed express orders by transitioning them to 'shipped'
    resolved_orders = []
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM orders WHERE priority = 'express' AND status NOT IN ('shipped', 'delivered')"
        ).fetchall()
        
        for row in rows:
            order_id = row["id"]
            db.execute(
                "UPDATE orders SET status = 'shipped' WHERE id = ?",
                (order_id,)
            )
            resolved_orders.append({
                "id": order_id,
                "customer": row["customer"],
                "item": row["item"],
                "previous_status": row["status"],
                "new_status": "shipped"
            })
    return {
        "status": "resolved",
        "message": f"Successfully self-healed {len(resolved_orders)} delayed express orders.",
        "resolved_orders": resolved_orders
    }

