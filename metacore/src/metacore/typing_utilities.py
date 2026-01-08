"""
Re-export utilities module for cleaner imports.

This allows: from metacore.typing_utilities import is_union
Instead of: from metacore.meta.typing.utilities import is_union
"""

from .meta.typing.utilities import (
    is_union,
    is_optional,
    is_binary_optional,
    resolve_annotation_types,
)

__all__ = [
    "is_union",
    "is_optional",
    "is_binary_optional",
    "resolve_annotation_types",
]
