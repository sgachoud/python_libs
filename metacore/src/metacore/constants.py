"""
Re-export constants module for cleaner imports.

This allows: from metacore.constants import ConstantNamespace
Instead of: from metacore.meta.classes.constants import ConstantNamespace
"""

from .meta.classes.constants import (
    ConstantNamespace,
    ConstantsMetaclass,
    ConstantsCompositionError,
    ConstantsInstantiationError,
    ConstantsModificationError,
)

__all__ = [
    "ConstantNamespace",
    "ConstantsMetaclass",
    "ConstantsCompositionError",
    "ConstantsInstantiationError",
    "ConstantsModificationError",
]
