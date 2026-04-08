from __future__ import annotations

import contextlib
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str | None) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


@contextlib.contextmanager
def request_context(*, request_id: str | None):
    token = _request_id_ctx.set(request_id)
    try:
        yield
    finally:
        _request_id_ctx.reset(token)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None):
            return True

        rid = get_request_id()
        if rid:
            setattr(record, "request_id", rid)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or get_request_id()
        payload: dict[str, Any] = {
            "timestamp": _utc_iso(),
            "level": record.levelname,
            "module": record.module,
            "request_id": request_id,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_info(message: str, *, request_id: str | None = None, logger_name: str = "medipilot-ai") -> None:
    logger = get_logger(logger_name)
    if request_id is None:
        logger.info(message)
        return
    with request_context(request_id=request_id):
        logger.info(message)


def log_error(
    message: str,
    *,
    request_id: str | None = None,
    logger_name: str = "medipilot-ai",
    exc: BaseException | None = None,
) -> None:
    logger = get_logger(logger_name)
    exc_info = exc if exc is not None else False
    if request_id is None:
        logger.error(message, exc_info=exc_info)
        return
    with request_context(request_id=request_id):
        logger.error(message, exc_info=exc_info)

