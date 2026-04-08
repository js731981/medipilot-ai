from __future__ import annotations

# Shim module: prefer importing from `utils.logger` everywhere.
# The canonical implementation currently lives in `backend.utils.logger`.

from backend.utils.logger import (  # noqa: F401
    JsonFormatter,
    RequestIdFilter,
    get_logger,
    get_request_id,
    log_error,
    log_info,
    request_context,
    set_request_id,
)

