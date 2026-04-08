from __future__ import annotations

"""
Run with:
  bentoml serve backend.main:svc --host 0.0.0.0 --port 3000
"""

import warnings

# `fs` (a transitive dependency used by BentoML) imports `pkg_resources` and
# emits a deprecation warning on import. We pin Setuptools to a safe version,
# and filter only this exact warning to keep server logs clean.
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API\..*",
    category=UserWarning,
)

from starlette.middleware.cors import CORSMiddleware

from backend.services.clinical_service import clinical_svc  # noqa: F401
from backend.services.coding_service import coding_svc  # noqa: F401
from backend.services.workflow_service import workflow_svc


# Default service to run (used by docker-compose and browser agent).
svc = workflow_svc

svc.add_asgi_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

