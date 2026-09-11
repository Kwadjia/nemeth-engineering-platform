"""Domain errors and their HTTP representation.

Errors are returned as RFC 9457 problem details (``application/problem+json``) with a
stable ``type`` per error class so clients can branch on it without parsing text.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

log = logging.getLogger(__name__)

PROBLEM_TYPE_BASE = "https://nemeth.dev/problems/"


class NemethError(Exception):
    """Base class for all domain errors."""

    status_code = 500
    problem_type = "internal-error"
    title = "Internal error"

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        self.extra = extra

    def to_problem(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": PROBLEM_TYPE_BASE + self.problem_type,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
        }
        body.update(self.extra)
        return body


class NotFoundError(NemethError):
    status_code = 404
    problem_type = "not-found"
    title = "Not found"


class ConflictError(NemethError):
    status_code = 409
    problem_type = "conflict"
    title = "Conflict"


class DomainValidationError(NemethError):
    status_code = 422
    problem_type = "validation"
    title = "Validation failed"


class ImmutableRevisionError(ConflictError):
    problem_type = "immutable-revision"
    title = "Revision is frozen"


class InvalidTransitionError(ConflictError):
    problem_type = "invalid-transition"
    title = "Invalid lifecycle transition"


class BomCycleError(ConflictError):
    problem_type = "bom-cycle"
    title = "BOM would contain a cycle"


class DuplicateIdentifierError(ConflictError):
    problem_type = "duplicate-identifier"
    title = "Identifier already exists"


def _problem_response(status: int, body: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NemethError)
    async def _domain_error(_: Request, exc: NemethError) -> JSONResponse:
        return _problem_response(exc.status_code, exc.to_problem())

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": ".".join(str(p) for p in e.get("loc", ())),
                "msg": e.get("msg"),
                "type": e.get("type"),
            }
            for e in exc.errors()
        ]
        return _problem_response(
            422,
            {
                "type": PROBLEM_TYPE_BASE + "request-validation",
                "title": "Request validation failed",
                "status": 422,
                "detail": "One or more fields are invalid.",
                "errors": errors,
            },
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        # Constraint names follow the naming convention in core/db.py, which makes the
        # message actionable without leaking SQL.
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        name = getattr(constraint, "constraint_name", None)
        log.warning("integrity error", extra={"constraint": name})
        return _problem_response(
            409,
            {
                "type": PROBLEM_TYPE_BASE + "integrity",
                "title": "Database constraint violated",
                "status": 409,
                "detail": f"Constraint violated: {name}" if name else "Constraint violated.",
                "constraint": name,
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return _problem_response(
            500,
            {
                "type": PROBLEM_TYPE_BASE + "internal-error",
                "title": "Internal error",
                "status": 500,
                "detail": "An unexpected error occurred. The request id has been logged.",
            },
        )
