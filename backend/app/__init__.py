"""Application package initialization and compatibility helpers."""

from __future__ import annotations

import inspect
import sys
from typing import ForwardRef


def _patch_forward_ref_evaluate() -> None:
    """Patch :class:`typing.ForwardRef` for Python 3.12 compatibility.

    Pydantic v1 expects :meth:`typing.ForwardRef._evaluate` to accept the
    ``recursive_guard`` argument positionally.  Python 3.12 changed the method
    signature so that the argument became keyword-only which results in
    ``TypeError: ForwardRef._evaluate() missing 1 required keyword-only
    argument: 'recursive_guard'`` when Pydantic tries to resolve forward
    references.  The latest Pydantic release already handles this change, but
    some environments still ship an affected combination.  Applying this patch
    allows the backend to run reliably across Python versions without requiring
    downstream pin adjustments.
    """

    if sys.version_info < (3, 12):
        return

    evaluate = getattr(ForwardRef, "_evaluate", None)
    if evaluate is None:
        return

    signature = inspect.signature(evaluate)
    parameters = list(signature.parameters.values())

    # ``recursive_guard`` became keyword-only in Python 3.12.  We detect the
    # signature shape at runtime so the patch is only applied when needed.
    has_keyword_only_recursive_guard = any(
        parameter.name == "recursive_guard" and parameter.kind == parameter.KEYWORD_ONLY
        for parameter in parameters
    )

    if not has_keyword_only_recursive_guard:
        return

    def _evaluate(self, globalns, localns, recursive_guard):  # type: ignore[override]
        return evaluate(self, globalns, localns, recursive_guard=recursive_guard)

    ForwardRef._evaluate = _evaluate  # type: ignore[assignment]


_patch_forward_ref_evaluate()
