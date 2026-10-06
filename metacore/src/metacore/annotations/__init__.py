"""Public API for annotation validation, conversion, defaults, and custom handlers."""

from ..typing import Annotation
from ._api import (
    annotation_registry,
    validator_from_annotation,
    defaulter_from_annotation,
    converter_from_annotation,
    validate_from_annotation,
    default_from_annotation,
    convert_to_annotation,
)
from ._entries import AnnotationEntry, HousingAnnotationEntry
from ._registry import AnnotationsRegistry
from ._types import (
    CastType, Converter, ConverterCreator, Defaulter, DefaulterCreator,
    ValidationLevel, Validator, ValidatorCreator,
)

__all__ = [
    "AnnotationsRegistry",
    "AnnotationEntry",
    "HousingAnnotationEntry",
    "ValidationLevel",
    "CastType",
    "Annotation",
    "Validator",
    "Defaulter",
    "Converter",
    "ValidatorCreator",
    "DefaulterCreator",
    "ConverterCreator",
    "annotation_registry",
    "validator_from_annotation",
    "defaulter_from_annotation",
    "converter_from_annotation",
    "validate_from_annotation",
    "default_from_annotation",
    "convert_to_annotation",
]
