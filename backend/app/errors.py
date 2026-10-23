"""One error shape for the whole API (docs/API.md 1) and the mappers that produce it."""

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logs import log_event


class AppError(Exception):
    def __init__(self, code: str, status: int, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.details = details or {}


def error_response(code: str, status: int, message: str,
                   details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "details": details or {}}},
        status_code=status,
    )


def problems_from(errors: list) -> list[dict]:
    """Pydantic errors as the `{field, problem}` list of a `validation_error` (API 1)."""
    return [{"field": ".".join(str(p) for p in err["loc"] if p != "body"), "problem": err["msg"]}
            for err in errors]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.code, exc.status, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response("validation_error", 422, "Some values are not valid.",
                              {"problems": problems_from(exc.errors())})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response("not_found", 404, "That does not exist.")
        return error_response("conflict", exc.status_code, "That request is not allowed here.")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        trace = "".join(traceback.format_exception(exc))
        log_event("error", "unhandled_exception", path=request.url.path,
                  error=type(exc).__name__, traceback=trace)
        return error_response("internal_error", 500, "Something went wrong. Nothing was lost.")
