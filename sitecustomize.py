"""
Project-wide Python startup customizations.

Python's `site` module will import `sitecustomize` automatically (if present on
`sys.path`). Keeping this at repo root ensures it runs early for CLI entrypoints
like `bentoml serve ...`, before third-party imports that may emit noisy warnings.
"""

from __future__ import annotations

import warnings


# `fs` (a transitive dependency) imports `pkg_resources` and emits a deprecation
# warning even when Setuptools is pinned below the removal version. Filter only
# this specific message to avoid hiding unrelated warnings.
warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API\..*",
    category=UserWarning,
)

