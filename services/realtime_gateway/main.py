"""Realtime Gateway Standalone Service Entrypoint."""

import uvicorn

from services.realtime_gateway.server import app

if __name__ == "__main__":
    uvicorn.run(
        "services.realtime_gateway.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
