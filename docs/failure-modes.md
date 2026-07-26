# Failure Modes

| Failure | Expected Behavior | Detection |
|---|---|---|
| Database unavailable | `/ready` reports degraded | Readiness probe, logs |
| Invalid transition | API returns `409` | Application metrics |
| Event processor stalled | Pending event count rises | Dashboard alert |
| Slow persistence | p95 latency rises | Load test, tracing |
| Bad deployment config | Readiness fails before traffic | Deployment validation |

