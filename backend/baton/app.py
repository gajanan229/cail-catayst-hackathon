"""FastAPI application factory. `uvicorn baton.app:app` (run from backend/)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import errors
from .api.routes import router
from .api.ws import ws_router
from .schemas.common import CONTRACT_VERSION


def create_app(start_runtime: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = None
        if start_runtime:
            from .api.deps import set_runtime
            from .runtime import Runtime

            runtime = Runtime.from_env()
            set_runtime(runtime)
            await runtime.start()
        try:
            yield
        finally:
            if runtime is not None:
                await runtime.stop()

    app = FastAPI(
        title="Baton API",
        version=CONTRACT_VERSION,
        description="Baton: AI operations co-pilot for HPE NonStop (simulated node \\TORBANK). "
        "REST contract per MVP spec §14; realtime contract in contracts/ws-events.schema.json.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    errors.install(app)
    app.include_router(router)
    app.include_router(ws_router)
    return app


app = create_app()
