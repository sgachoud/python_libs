"""
MIT License

Copyright (c) 2025 Sébastien Gachoud

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from functools import lru_cache
from typing import Any

from ..typing import Annotation
from ._registry import AnnotationsRegistry
from ._types import Converter, Defaulter, ValidationLevel, Validator

@lru_cache(1)
def annotation_registry() -> AnnotationsRegistry:
    """Default annotation registry. Allows to register custom type defaulters and converters.
    See AnnotationsRegistry for more information.

    Returns:
        AnnotationsRegistry: the type registry instance.
    """
    return AnnotationsRegistry()


def validator_from_annotation(annotation: Annotation) -> Validator:
    """This function is a shortcut to `annotation_registry().validator_from_annotation()`."""
    return annotation_registry().validator_from_annotation(annotation)


def defaulter_from_annotation(annotation: Annotation) -> Defaulter:
    """This function is a shortcut to `annotation_registry().defaulter_from_annotation()`."""
    return annotation_registry().defaulter_from_annotation(annotation)


def validate_from_annotation(
    annotation: Annotation, value: Any
) -> bool | ValidationLevel:
    """This function is a shortcut to `annotation_registry().validate_with_annotation()`."""
    return annotation_registry().validate_with_annotation(annotation, value)


def default_from_annotation(annotation: Annotation) -> Any:
    """This function is a shortcut to `annotation_registry().default_annotation()`."""
    return annotation_registry().default_annotation(annotation)


def convert_to_annotation(annotation: Annotation, value: Any) -> Any:
    """This function is a shortcut to `annotation_registry().convert_to_annotation()`."""
    return annotation_registry().convert_to_annotation(annotation, value)


def converter_from_annotation(annotation: Annotation) -> Converter:
    """Return a converter from the default registry for the annotation."""
    return annotation_registry().converter_from_annotation(annotation)
