# Sev-1 / Sev-2 Production Incident Response Runbook

> **Platform**: Multilingual AI Meeting Platform  
> **On-Call Protocol**: PagerDuty Escalation & War Room Protocol

---

## 1. Incident Severity Definitions

- **SEV-1 (Critical)**: Meeting audio unroutable, control plane down, or cross-tenant data leak breach (Invariant #1 violation). MTTR SLA: $< 15$ minutes.
- **SEV-2 (Major)**: Real-time caption or translation delayed ($> 2000$ms), or single worker fleet degraded (e.g., TTS synthesis failure). MTTR SLA: $< 30$ minutes.
- **SEV-3 (Minor)**: Non-critical dashboard telemetry failure, localized admin portal rendering defect. MTTR SLA: $< 4$ hours.

---

## 2. Specific Triage Playbooks

### Playbook A: Dead Letter Queue (DLQ) Poison Pill Flooding
- **Symptoms**: `quarantined_count` spike in Orchestrator metrics.
- **Root Cause**: Corrupted audio bitstream or schema mismatch packet circulating in Redis streams.
- **Mitigation**:
  1. Inspect quarantined DLQ events:
     ```bash
     redis-cli -h $REDIS_HOST XRANGE events:meeting:<MEETING_ID>:dlq - + COUNT 10
     ```
  2. Confirm `retry_count >= 3` was applied before quarantine (Invariant #4).
  3. Purge bad messages or patch client encoding if systemic.

### Playbook B: AI Worker Fleet Crash / Hang
- **Symptoms**: `WorkerHealthStatus.DEAD` emitted by `WorkerHealthMonitor` after 3.0s timeout.
- **Mitigation**:
  1. Check worker logs:
     ```bash
     kubectl logs -l app.kubernetes.io/component=worker-stt --tail=100
     ```
  2. Verify GPU memory or CPU utilization. If OOM killed:
     ```bash
     kubectl describe pod -l app.kubernetes.io/component=worker-stt | grep -i oom
     ```
  3. Scale up replicas immediately:
     ```bash
     kubectl scale deployment meeting-platform-worker-stt --replicas=8
     ```

### Playbook C: Acoustic Watermark Feedback Storm
- **Symptoms**: Watermark detector rejecting $> 50\%$ incoming frames.
- **Mitigation**:
  - `AudioIngestionPipeline` will reject watermarked frames automatically without crashing (Invariant #3).
  - Inspect offending participant audio track in LiveKit dashboard and mute remotely via Admin API:
    ```bash
    curl -X POST https://api.meeting.enterprise.ai/api/v1/admin/participants/<ID>/mute
    ```
