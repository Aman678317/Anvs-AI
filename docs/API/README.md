# API & Event Contracts Specification Index

Adhering to **Document 08 (API + Event Contracts v1.2)** and **Document 12 (Final Master Specification)**.

## 1. Control Plane REST Endpoints (`services/api`)

- `POST /api/v1/auth/token` - Authenticate participant session
- `POST /api/v1/meetings` - Create new multilingual meeting room
- `GET /api/v1/meetings/{id}` - Retrieve meeting state & configuration
- `POST /api/v1/meetings/{id}/join` - Join meeting and issue LiveKit token + WS ticket
- `POST /api/v1/meetings/{id}/end` - Host end meeting lifecycle
- `GET /api/v1/meetings/{id}/transcript` - Fetch full meeting transcript with lineage
- `GET /healthz` - Health probe endpoint

## 2. Realtime WebSocket Gateway (`services/realtime-gateway`)

- Endpoint: `ws://{host}:8001/ws/meetings/{meeting_id}?ticket={ws_ticket}`
- Client Messages:
  - `join_room`
  - `set_listening_language`
  - `send_chat_message`
  - `query_assistant`
- Server Broadcast Events:
  - `room_state`
  - `participant_joined` / `participant_left`
  - `caption_update` (contains `source_segment_id`, `translated_text`, `is_final`)
  - `assistant_response`
