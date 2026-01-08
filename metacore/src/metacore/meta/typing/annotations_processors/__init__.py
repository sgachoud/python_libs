"""Annotation processing system for metacore."""

# Import known_types to register built-in type handlers
from . import known_types as _ # noqa: F401

from .processors import (
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
)
from .errors import (
    TypingError,
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
