"""Error envelope (MVP spec §14): {"error": {code, message, detail, correlation_id}}."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..core.ids import new_id

STATUS = {
    "VALIDATION_FAILED": 422,
    "POLICY_DENIED": 403,
    "APPROVAL_EXPIRED": 409,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "SIM_NOT_RUNNING": 409,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def _body(code: str, message: str, detail: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail, "correlation_id": new_id("cor")}}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message, exc.detail), status_code=STATUS.get(exc.code, 400))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg")} for e in exc.errors()]
        return JSONResponse(_body("VALIDATION_FAILED", "Request validation failed", {"errors": errors}), status_code=422)
