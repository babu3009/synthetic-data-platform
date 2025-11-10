# Tracing & Rate Limiting Configuration

This guide centralizes how to enable OpenTelemetry tracing and tune per-project inference rate limiting for the Synthetic Data Platform backend.

## Tracing

OpenTelemetry tracing is disabled by default. Enable it when you have an OTLP collector (local or hosted) available.

### Required Environment Variables (backend `.env`)

```
ENABLE_TRACING=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http
OTEL_SERVICE_NAME=synthetic-data-backend
```

| Variable | Purpose | Default |
|----------|---------|---------|
| ENABLE_TRACING | Master switch for tracing instrumentation | false |
| OTEL_EXPORTER_OTLP_ENDPOINT | Collector endpoint (HTTP or gRPC) | (unset) |
| OTEL_EXPORTER_OTLP_PROTOCOL | Transport protocol (`http` or `grpc`) | http |
| OTEL_SERVICE_NAME | Logical service name for resource attributes | synthetic-data-backend |

### Minimal Local Setup (Optional)

Use an OTLP-compatible collector (e.g., OpenTelemetry Collector, SigNoz, Tempo). Ensure the endpoint matches the protocol above. Example Docker Compose snippet:

```yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    ports:
      - "4318:4318"   # OTLP HTTP
      - "4317:4317"   # OTLP gRPC
```

### Verification

After enabling tracing and restarting the backend:

1. Exercise a few API routes (e.g., providers inference, LLM settings update).
2. Confirm spans arrive in your backend (collector or visualization UI).

If spans are missing:
- Check endpoint reachability (`curl http://localhost:4318/v1/traces -v` should not 404 if collector active).
- Verify no proxy or firewall rules are blocking traffic.

## Rate Limiting

Per-project inference requests (`POST /api/v1/projects/{projectId}/infer/providers`) are limited to a configurable number per rolling minute window.

OTP resend limits

In addition to inference limits, auth OTP resends are governed by `OTP_RESEND_RATE_PER_HOUR` over a rolling 1-hour window. The initial registration OTP is excluded from resend accounting; up to `OTP_RESEND_RATE_PER_HOUR` additional resends are allowed during the window.

### Environment Variables

```
INFER_RATE_LIMIT_PER_MINUTE=60
FF_ENABLE_RATE_LIMIT_AUDIT=true
```

| Variable | Purpose | Default |
|----------|---------|---------|
| INFER_RATE_LIMIT_PER_MINUTE | Allowed requests per project per minute | 60 |
| FF_ENABLE_RATE_LIMIT_AUDIT | Emit audit events when limit exceeded | true |

### Behavior

- Once the threshold is exceeded within the current minute bucket, the endpoint returns HTTP 429:

```json
{"detail": "Rate limit exceeded; try again later"}
```
- When `FF_ENABLE_RATE_LIMIT_AUDIT` is true, an audit event is inserted with action `llm.infer.rate_limited` and payload `{ "limit": <int> }`.

For OTP resends, the auth endpoints return HTTP 429 when the resend allowance is exhausted for the current window.

### Adjusting the Limit

Increase or decrease the limit by editing `.env` and restarting the backend service:

```
INFER_RATE_LIMIT_PER_MINUTE=120
```

### Production Considerations

The current limiter is in-memory. For horizontally scaled deployments, migrate to a centralized store (e.g., Redis) using atomic increments and TTL (Lua script or `INCR` + key expiration).

Pseudo-flow with Redis:

```
key = f"infer:{project_id}:{current_minute_bucket}"
count = INCR(key)
EXPIRE key 65  # seconds
if count > LIMIT: reject
```

## Probe Audit Events

LLM provider probes (`POST /api/v1/admin/llm/providers/{providerId}:probe`) now emit audit events when `FF_ENABLE_PROBE_AUDIT=true`:

- Action: `llm.provider.probe`
- Payload keys: `provider_id`, `ok`, `message`

Disabled provider example payload:
```json
{"provider_id": "<uuid>", "ok": false, "message": "provider disabled"}
```

Successful no-op example:
```json
{"provider_id": "<uuid>", "ok": true, "message": "no-op"}
```

## Observability Checklist

| Goal | Step |
|------|------|
| Enable metrics | Ensure `ENABLE_METRICS=true` (default) |
| Enable tracing | Set `ENABLE_TRACING=true` + OTLP vars |
| Confirm rate limit | Trigger > limit requests; expect 429 + audit row |
| Verify probe auditing | Call probe on enabled & disabled provider; check audit entries |

## Troubleshooting

| Symptom | Possible Cause | Resolution |
|---------|----------------|------------|
| No spans exported | Wrong OTLP endpoint | Match protocol/port (4318 for HTTP) |
| 429 too early | Time skew in test monkeypatch | Ensure monotonic time or reset limiter before test |
| Missing audit entries | Feature flag off | Set `FF_ENABLE_RATE_LIMIT_AUDIT=true` / `FF_ENABLE_PROBE_AUDIT=true` |

## Next Steps

- Migrate rate limiter to Redis for multi-instance deployments.
- Add latency and error classification to probe responses.
- Emit tracing spans around external LLM calls for performance analysis.

---
**Revision:** Nov 7, 2025
