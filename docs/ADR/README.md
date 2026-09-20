# Architecture Decision Records (ADRs)

This directory contains the immutable Architecture Decision Records (ADRs) established and frozen in **Document 13 (Architecture Freeze + Coding Readiness v1.0)**.

| ADR ID      | Title                                       | Status                | Primary Rationale                                                        |
| :---------- | :------------------------------------------ | :-------------------- | :----------------------------------------------------------------------- |
| **ADR-001** | Next.js 14 App Router for Web Frontend      | **Accepted (Frozen)** | React Server Components, LiveKit SDK compatibility, low latency          |
| **ADR-002** | FastAPI 0.111+ Python 3.11 Control Plane    | **Accepted (Frozen)** | Async IO, strict Pydantic v2 schemas, AI worker ecosystem                |
| **ADR-003** | LiveKit SFU for WebRTC Media Transport      | **Accepted (Frozen)** | Distributed Go SFU, simulcast, dynamic participant audio publishing      |
| **ADR-004** | Redis 7.2 Streams for Event Distribution    | **Accepted (Frozen)** | Sub-millisecond queuing, consumer groups, durable segment streams        |
| **ADR-005** | Supabase PostgreSQL 16 + RLS Multi-Tenancy  | **Accepted (Frozen)** | Native vector search (`pgvector`), declarative row-level isolation       |
| **ADR-006** | 20 kHz Ultrasonic Watermarking on TTS Audio | **Accepted (Frozen)** | Mathematical loop prevention, stops synthetic speech re-entering STT     |
| **ADR-007** | OpenTelemetry 1.44 Distributed Tracing      | **Accepted (Frozen)** | Unified end-to-end trace propagation across WebRTC, API, Redis & AI      |
| **ADR-008** | Faster-Whisper + NLLB-200 + XTTS-v2 Stack   | **Accepted (Frozen)** | Best-in-class open-source latency/accuracy balance across 200+ languages |
