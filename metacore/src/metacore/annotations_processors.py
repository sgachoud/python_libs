"""
Re-export annotations_processors module for cleaner imports.

This allows: from metacore.annotations_processors import annotation_registry
Instead of: from metacore.meta.typing.annotations_processors import ...
"""

from.meta.typing.errors import (
    TypingError,
)

from .meta.typing.annotations_processors import (
    AnnotationsRegistry,
    AnnotationEntry,
    HousingAnnotationEntry,
    ValidationLevel,
    annotation_registry,
    validator_from_annotation,
    defaulter_from_annotation,
    validate_from_annotation,
    default_from_annotation,
    convert_to_annotation,
    AnnotationProcessorError,
    ConvertingToAnnotationTypeError,
    DefaultingAnnotationError,
)

__all__ = [
    # Core classes
    "AnnotationsRegistry",
    "AnnotationEntry",
    "HousingAnnotationEntry",
    "ValidationLevel",
    # Main API functions
    "annotation_registry",
    "validator_from_annotation",
    "defaulter_from_annotation",
    "validate_from_annotation",
    "default_from_annotation",
    "convert_to_annotation",
    # Errors
    "TypingError",
    "AnnotationProcessorError",
    "ConvertingToAnnotationTypeError",
    "DefaultingAnnotationError",
]
