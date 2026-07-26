# Local Run Notes

## Verified Local Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m compileall src tests scripts
python3 scripts/kafka_event_probe.py
```

## API Smoke Flow

The API creates a critical incident ticket, assigns it, adds an investigation comment, drains three emitted events, and exposes Prometheus-style metrics.

Expected event flow:

1. `ticket.created`
2. `ticket.assigned`
3. `ticket.comment_added`

## Compose Stack

`docker compose up --build` runs API, Postgres, Redis, Redpanda, Prometheus, Grafana, and OpenTelemetry collector.

Validated locally:

- `/ready` returned `{"status":"ready","dependencies":{"database":"ok","event_bus":"ok"},"pending_events":0}`
- `scripts/demo_flow.py` created and assigned a critical ticket
- `/metrics` exposed ticket counts, pending events, and overdue tickets

One startup issue found during validation: the API could start before Postgres accepted TCP connections. The Postgres repository now retries initialization before failing.
