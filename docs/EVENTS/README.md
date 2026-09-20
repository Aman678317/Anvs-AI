# Event Streams Specification Index

Redis Streams event topics and channel patterns established in **Document 08** and **Document 14**:

| Stream Key Pattern | Payload Type | Producers | Consumers |
| :--- | :--- | :--- | :--- |
| `events:meeting:{id}:source_segment` | `SourceSegmentEvent` | `stt-worker` | `translation-worker`, `speaker-worker`, `realtime-gateway` |
| `events:meeting:{id}:translation_segment` | `TranslationSegmentEvent` | `translation-worker` | `tts-worker`, `realtime-gateway`, `assistant-worker` |
| `events:meeting:{id}:audio_segment` | `AudioSegmentEvent` | `tts-worker` | `livekit-sfu` (Egress / Publisher) |
| `events:meeting:{id}:room_state` | `RoomStateEvent` | `api`, `orchestrator` | `realtime-gateway` |
