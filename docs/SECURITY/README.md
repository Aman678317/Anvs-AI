# Security & Privacy Specification Baseline

Adhering to **Document 09 (Security & Privacy Specification v1.0)**.

## Core Security Controls

1. **Zero-Trust Multi-Tenancy**:

   - Every database table enforces PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY`).
   - Tenant isolation is strictly anchored to `request.jwt.claims.tenant_id`.

2. **Acoustic Watermarking**:

   - 20 kHz ultrasonic continuous watermark on synthesized audio output.
   - Prevents synthetic feedback into microphone audio and protects voice clone abuse.

3. **Data Protection & Encryption**:

   - Data in transit: TLS 1.3 for HTTPS / WSS, DTLS-SRTP for WebRTC audio/video.
   - Data at rest: AES-256-GCM column-level encryption for transcript text and vector embeddings.

4. **Authentication & Token Ephemerality**:
   - Supabase Auth JWT with 60-minute lifetime.
   - LiveKit access tokens scoped strictly to room name and participant identity with 2-hour max TTL.
