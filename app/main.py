"""Top-level FastAPI application entrypoint alias.

Provides seamless compatibility for running the Control Plane API via either:
    uvicorn app.main:app --reload
or:
    uvicorn services.api.main:app --reload
"""

import uvicorn

from services.api.main import app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
