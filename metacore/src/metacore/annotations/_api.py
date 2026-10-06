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


def validator_from_annotation(
    annotation: Annotation,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> Validator:
    """This function is a shortcut to `annotation_registry().validator_from_annotation()`."""
    return annotation_registry().validator_from_annotation(
        annotation, nglobals=nglobals, nlocals=nlocals
    )


def defaulter_from_annotation(
    annotation: Annotation,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> Defaulter:
    """This function is a shortcut to `annotation_registry().defaulter_from_annotation()`."""
    return annotation_registry().defaulter_from_annotation(
        annotation, nglobals=nglobals, nlocals=nlocals
    )


def validate_from_annotation(
    annotation: Annotation,
    value: Any,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> bool | ValidationLevel:
    """This function is a shortcut to `annotation_registry().validate_with_annotation()`.

    PARTIAL is truthy. Use fully_matches_annotation for a boolean full match.
    """
    return annotation_registry().validate_with_annotation(
        annotation, value, nglobals=nglobals, nlocals=nlocals
    )


def fully_matches_annotation(
    annotation: Annotation,
    value: Any,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> bool:
    """Return a boolean full match; partial matches are False, errors still raise."""
    return annotation_registry().fully_matches_annotation(
        annotation, value, nglobals=nglobals, nlocals=nlocals
    )


def default_from_annotation(
    annotation: Annotation,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> Any:
    """This function is a shortcut to `annotation_registry().default_annotation()`."""
    return annotation_registry().default_annotation(
        annotation, nglobals=nglobals, nlocals=nlocals
    )


def convert_to_annotation(
    annotation: Annotation,
    value: Any,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> Any:
    """This function is a shortcut to `annotation_registry().convert_to_annotation()`."""
    return annotation_registry().convert_to_annotation(
        annotation, value, nglobals=nglobals, nlocals=nlocals
    )


def converter_from_annotation(
    annotation: Annotation,
    *,
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> Converter:
    """Return a converter from the default registry for the annotation."""
    return annotation_registry().converter_from_annotation(
        annotation, nglobals=nglobals, nlocals=nlocals
    )
