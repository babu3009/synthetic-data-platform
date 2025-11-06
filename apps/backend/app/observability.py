from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI

# Prometheus metrics via fastapi-instrumentator
try:
    from prometheus_client import Counter  # type: ignore
    from fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover - optional dep
    Counter = None  # type: ignore
    Instrumentator = None  # type: ignore

# OpenTelemetry tracing
try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.resources import Resource  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor  # type: ignore
    from opentelemetry.instrumentation.redis import RedisInstrumentor  # type: ignore
    from opentelemetry.instrumentation.requests import RequestsInstrumentor  # type: ignore
except Exception:  # pragma: no cover - optional dep
    trace = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    Psycopg2Instrumentor = None  # type: ignore
    RedisInstrumentor = None  # type: ignore
    RequestsInstrumentor = None  # type: ignore


# Global custom metrics (exposed if prometheus_client present)
REQUESTS_STARTED = None
REQUESTS_COMPLETED = None
REQUESTS_FAILED = None


def init_observability(app: FastAPI) -> None:
    """Initialize Prometheus metrics and OpenTelemetry tracing for the app.

    - Exposes /metrics when fastapi-instrumentator is installed
    - Sets up OTLP tracing if OTEL_EXPORTER_OTLP_ENDPOINT is configured
    """
    global REQUESTS_STARTED, REQUESTS_COMPLETED, REQUESTS_FAILED

    # Prometheus metrics
    if Instrumentator is not None:
        try:
            Instrumentator().instrument(app).expose(app, include_in_schema=False)
        except Exception:
            pass
    if Counter is not None:
        try:
            REQUESTS_STARTED = Counter(
                "synth_requests_started_total", "Requests started", ["type"]
            )
            REQUESTS_COMPLETED = Counter(
                "synth_requests_completed_total", "Requests completed", ["type"]
            )
            REQUESTS_FAILED = Counter(
                "synth_requests_failed_total", "Requests failed", ["type"]
            )
        except Exception:
            # If metrics already registered, ignore
            pass

    # OpenTelemetry tracing
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if trace is not None and TracerProvider is not None and Resource is not None and OTLPSpanExporter is not None and BatchSpanProcessor is not None and endpoint:
        try:
            resource = Resource.create({"service.name": "synthetic-data-backend"})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=endpoint)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            # Instrumentations
            if FastAPIInstrumentor is not None:
                FastAPIInstrumentor.instrument_app(app)
            if Psycopg2Instrumentor is not None:
                Psycopg2Instrumentor().instrument()
            if RedisInstrumentor is not None:
                RedisInstrumentor().instrument()
            if RequestsInstrumentor is not None:
                RequestsInstrumentor().instrument()
        except Exception:
            # Best-effort; continue without tracing if setup fails
            pass


def get_tracer(name: str = __name__):
    """Return an OpenTelemetry tracer if available, else a no-op shim."""
    if trace is None:
        class _NoopSpan:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
        class _NoopTracer:
            def start_as_current_span(self, *_args, **_kwargs):
                return _NoopSpan()
        return _NoopTracer()
    return trace.get_tracer(name)
