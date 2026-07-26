# Design Notes

The service keeps the ticketing domain small: tickets, comments, state transitions, and event emission. The useful part is the boundary between HTTP handlers, domain logic, storage, and event delivery.

## Current Choices

- FastAPI provides a typed API surface and OpenAPI documentation.
- SQLite is used by default so tests and local runs do not need Docker.
- `DATABASE_URL` switches storage to Postgres.
- `REDIS_URL` switches event storage to Redis.
- Domain transitions are validated in the service layer, not hidden in route handlers.
- Events are published for ticket creation, assignment, and state transitions.
- Health and readiness endpoints distinguish process health from dependency readiness.

## Follow-Up Work

- Use the Redpanda service for event publishing instead of only documenting the Kafka contract.
- Add request latency buckets instead of the current simple gauges.
- Add a migration tool once the schema changes more often.
- Add integration tests that bring up Postgres and Redis through Compose.
