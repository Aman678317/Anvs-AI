# Disaster Recovery & Business Continuity Runbook

> **Platform**: Multilingual AI Meeting Platform  
> **Recovery Time Objective (RTO)**: $\le 15$ minutes  
> **Recovery Point Objective (RPO)**: $\le 60$ seconds (Continuous WAL Archiving)

---

## 1. Managed PostgreSQL Disaster Recovery

### 1.1 Snapshot Restore with `pgvector`
In the event of catastrophic data corruption or primary DB instance failure:
1. Locate the latest automated snapshot:
   ```bash
   aws rds describe-db-snapshots \
     --db-instance-identifier production-meeting-db \
     --query "reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].DBSnapshotIdentifier" \
     --output text
   ```
2. Restore to a new target instance:
   ```bash
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier production-meeting-db-restored \
     --db-snapshot-identifier <SNAPSHOT_ID> \
     --db-instance-class db.r6g.xlarge \
     --multi-az \
     --auto-minor-version-upgrade
   ```
3. Update Kubernetes Secret `meeting-db-credentials` with the new endpoint and execute rolling restart:
   ```bash
   kubectl rollout restart deployment -l app.kubernetes.io/part-of=multilingual-meeting-platform
   ```

### 1.2 Mandatory Post-Restore RLS Verification (Invariant #1)
Always verify PostgreSQL Row Level Security is active before opening traffic:
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('meetings', 'users', 'participants', 'transcript_segments');
```
*Expected Result*: All tenant tables must return `rowsecurity = true`.

---

## 2. Redis Streams Bus Recovery & PEL Re-claim

When Redis undergoes a failover or pod eviction:
1. ElastiCache multi-AZ automatic failover promotes replica to master in $< 30$ seconds.
2. In-flight messages in Pending Entries List (PEL) are automatically claimed by `PipelineOrchestrator` via `xautoclaim`:
   ```bash
   kubectl logs -l app.kubernetes.io/component=orchestrator | grep "reclaimed"
   ```
3. Verify Redis memory consumption and stream lengths:
   ```bash
   redis-cli -h $REDIS_HOST INFO memory
   redis-cli -h $REDIS_HOST XLEN events:transcripts
   ```

---

## 3. WebRTC LiveKit SFU Recovery

If an SFU node terminates abruptly:
1. Client WebSocket sessions receive `WSServerMessageType.ERROR` or trigger automatic ICE reconnection.
2. New token re-issuance is validated through Control Plane API (`/api/v1/auth/ticket`).
3. Kubernetes replaces the LiveKit pod; session state is re-synced via Redis room state channel.
