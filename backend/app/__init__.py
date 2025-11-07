"""Application package initialization and compatibility helpers.

This module applies a small runtime patch for Python 3.12 where
``typing.ForwardRef._evaluate`` changed its signature. Pydantic v1 calls
``_evaluate`` with a positional third argument, which raises:

    TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'

The patch adapts the call shape so existing code continues to work without
pinning older Python versions. It is a no-op on Python < 3.12 or when the
signature is already positional.
"""

from __future__ import annotations

import inspect
import sys
from typing import ForwardRef


def _patch_forward_ref_evaluate() -> None:
    if sys.version_info < (3, 12):
        return

    evaluate = getattr(ForwardRef, "_evaluate", None)
    if evaluate is None:
        return

    signature = inspect.signature(evaluate)
    parameters = list(signature.parameters.values())

    has_keyword_only_recursive_guard = any(
        p.name == "recursive_guard" and p.kind == p.KEYWORD_ONLY for p in parameters
    )

    if not has_keyword_only_recursive_guard:
        return

    def _evaluate(self, *args, **kwargs):  # type: ignore[override]
        # Support both call styles:
        #  - _evaluate(globalns, localns, recursive_guard)
        #  - _evaluate(globalns, localns, *, recursive_guard=...)
        if len(args) == 3 and "recursive_guard" not in kwargs:
            globalns, localns, recursive_guard = args
            return evaluate(self, globalns, localns, recursive_guard=recursive_guard)
        if len(args) == 2 and "recursive_guard" in kwargs:
            globalns, localns = args
            return evaluate(self, globalns, localns, recursive_guard=kwargs["recursive_guard"]) 
        # Fallback to whatever was passed through.
        return evaluate(self, *args, **kwargs)

    ForwardRef._evaluate = _evaluate  # type: ignore[assignment]


_patch_forward_ref_evaluate()
