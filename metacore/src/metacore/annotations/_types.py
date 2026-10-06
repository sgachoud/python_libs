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

from enum import IntEnum
from typing import Any, Callable

class ValidationLevel(IntEnum):
    """Validation level for type checking.

    NONE: No validation. The value does not match the annotation.
    FULL: The value matches the annotation.
    PARTIAL: The value matches the top level annotation. For example, [1, "2"] matches partialy
        list[str] because it is a list but it does not contains only strings. ("1", "2") does not
        match because it is not a list.

    FULL and PARTIAL are both truthy. Compare with FULL, or use
    fully_matches_annotation, when partial matches must be rejected.
    """

    NONE = 0
    FULL = 1
    PARTIAL = 2


def vl_and(vl1: int, vl2: int) -> int:
    """Logical and between two validation levels with a cast to int."""
    return int(vl1) & int(vl2)


def vl_or(vl1: int, vl2: int) -> int:
    """Logical or between two validation levels with a cast to int."""
    return int(vl1) | int(vl2)


type Validator = Callable[[Any], bool] | Callable[[Any], ValidationLevel]
type Defaulter = Callable[[], Any]
type Converter = Callable[[Any], Any]

type ValidatorCreator = Callable[..., Validator]
type DefaulterCreator = Callable[..., Defaulter]
type ConverterCreator = Callable[..., Converter]


class CastType[T]:
    """Typing type to force a cast. Useful in a union for example.

    In a union the first type wrapped with CastType will be used to cast the value.
    """
