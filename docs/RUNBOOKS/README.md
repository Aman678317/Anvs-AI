# SRE & Operations Runbooks

Operational procedures for local and production deployment:

1. **Local Boot**: `make up` followed by `make dev`.
2. **Database Migrations**: `make db-migrate` and `make db-upgrade`.
3. **Queue Health Inspection**: Monitor consumer group lag in Redis Streams via `redis-cli XINFO GROUPS events:meeting:{id}:source_segment`.
4. **LiveKit SFU Diagnostics**: Inspect WebRTC connection states and egress pipelines via Prometheus metrics on port 7880 / 9090.
