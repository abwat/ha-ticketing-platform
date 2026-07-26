# Runbook

## API Is Healthy But Not Ready

1. Check `/ready` and identify the failing dependency.
2. Check database connectivity and migrations.
3. Review recent deploys and configuration changes.
4. Roll back if readiness failed immediately after release.

## Event Lag Is Growing

1. Check `/health` for `pending_events`.
2. Drain events with `POST /events/drain` in local demos.
3. In production, inspect worker logs and queue depth.
4. Scale workers if queue depth grows while dependencies are healthy.

## Ticket Creation Errors

1. Inspect 4xx vs 5xx rate.
2. For 4xx, validate client payloads and enum values.
3. For 5xx, check database health and write latency.
4. Confirm recent schema or configuration changes.

