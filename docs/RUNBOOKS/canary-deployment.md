# Canary Deployment & Progressive Rollout Playbook

> **Platform**: Multilingual AI Meeting Platform  
> **Deployment Strategy**: Weighted Ingress Traffic Shifting & Zero Downtime Pod Updates

---

## 1. Canary Traffic Shifting Stages

| Stage | Traffic Weight | Soak Duration | Criteria to Advance |
| :--- | :--- | :--- | :--- |
| **Stage 1 (Internal)** | 5% (Internal Tenants) | 15 minutes | Zero 5xx, P95 audio latency $< 1200$ms |
| **Stage 2 (Canary)** | 25% of all traffic | 30 minutes | STT WER $< 12\%$, zero unhandled exceptions |
| **Stage 3 (Half)** | 50% of all traffic | 30 minutes | Realtime WS caption latency $< 50$ms |
| **Stage 4 (Full)** | 100% (Production) | Continuous | General release certified |

---

## 2. Automated Rollback Thresholds

Execute immediate rollback if any of the following triggers occur during canary:
1. **HTTP 5xx Rate**: $> 0.1\%$ of total requests over 3 consecutive minutes.
2. **E2E Audio Latency**: P95 glass-to-glass latency $> 1500$ms.
3. **Dead Letter Queue Rate**: $> 5$ events per minute routed to DLQ.
4. **WebSocket Disconnect Spike**: $> 2\%$ unexpected client disconnects within 60 seconds.

---

## 3. Deployment & Rollback Commands

### 3.1 Helm Progressive Upgrade
```bash
# Deploy canary with new image tag
helm upgrade --install meeting-platform ./infrastructure/helm/multilingual-meeting-platform \
  --set global.imageTag="1.0.1" \
  --set api.autoscaling.minReplicas=5 \
  --wait --timeout 5m
```

### 3.2 Instant Rollback Command
If any SLA or error budget metric degrades:
```bash
# Roll back immediately to previous revision
helm rollback meeting-platform 0

# Verify rollout status
kubectl rollout status deployment -l app.kubernetes.io/part-of=multilingual-meeting-platform
```
