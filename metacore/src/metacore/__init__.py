"""
metacore: Core utilities for Python metaprogramming.

This library provides:
- Type annotation processing with validators, converters, and defaulters
- ConstantNamespace for immutable class-level constants
- TracedException for enhanced exception formatting
- Type checking utilities
"""

__version__ = "0.1.0"
__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from .annotations import (
    ValidationLevel,
    annotation_registry,
    validator_from_annotation,
    defaulter_from_annotation,
    converter_from_annotation,
    validate_from_annotation,
    fully_matches_annotation,
    default_from_annotation,
    convert_to_annotation,
)
from .constants import ConstantNamespace
from .exceptions import TracedException

__all__ = [
    "ConstantNamespace",
    "TracedException",
    "ValidationLevel",
    "annotation_registry",
    "validator_from_annotation",
    "defaulter_from_annotation",
    "converter_from_annotation",
    "validate_from_annotation",
    "fully_matches_annotation",
    "default_from_annotation",
    "convert_to_annotation",
    "__version__",
    "__author__",
    "__license__",
]
