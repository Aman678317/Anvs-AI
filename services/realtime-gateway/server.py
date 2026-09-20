"""FastAPI WebSocket Server (Hyphen Directory Mirror)."""

from services.realtime_gateway.server import app, create_realtime_gateway_app

__all__ = ["app", "create_realtime_gateway_app"]
