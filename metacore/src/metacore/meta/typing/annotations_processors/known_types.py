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

-------------------------------------------------------------------------------

Author: Sébastien Gachoud
Created: 2025-07-15
Description: Built-in type handlers for the annotation registry. This module registers
            processors for common Python types including Any, tuple, list, set, dict,
            Literal, Callable, Final, ClassVar, and CastType.
🦙
"""

from functools import reduce
from types import NotImplementedType, NoneType, EllipsisType
from typing import Self, Any, ClassVar, Final, Literal, get_args

from .errors import ConvertingToAnnotationTypeError
from .processors import (
    Annotation,
    AnnotationEntry,
    AnnotationsRegistry,
    Converter,
    Defaulter,
    ValidationLevel,
    Validator,
    vl_and,
    annotation_registry,
    validator_from_annotation,
)


class CastType[T]:
    """Typing type to force a cast. Useful in a union for example.

    In a union the first type wrapped with CastType will be used to cast the value.
    """


# Register a few known types

ar = annotation_registry()


# CastType
class CastTypeAnnotationEntry(AnnotationEntry):
    """CastType annotation entry. Provides a validator, defaulter and converter creator for
    CastType.
    """

    @staticmethod
    def validate(_: Any, /) -> ValidationLevel:
        """Always valid."""
        return ValidationLevel.FULL

    def create_defaulter(
        self,
        inner_defaulter: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry, /
    ) -> Defaulter | NotImplementedType:
        return inner_defaulter[0]

    def create_converter(
        self,
        inner_converters: list[Converter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry, /
    ) -> Converter | NotImplementedType:
        return inner_converters[0]


# Any
class AnyAnnotationEntry(AnnotationEntry):
    """Any annotation entry. Provides a validator, defaulter and converter creator for Any."""

    @staticmethod
    def validate(_: Any, /) -> ValidationLevel:
        """Always valid."""
        return ValidationLevel.FULL

    @staticmethod
    def default() -> Any:
        """Always returns None."""
        return None

    @staticmethod
    def convert(value: Any, /) -> Any:
        """Always returns the value."""
        return value


ar.register_processor(Any, AnyAnnotationEntry())


# tuple
class TupleAnnotationEntry(AnnotationEntry):
    """Tuple annotation entry. Provides a validator, defaulter and converter creators for tuples."""

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        """Create a tuple validator from inner validators."""

        def validator(vs: Any) -> ValidationLevel:
            if not isinstance(vs, tuple) or len(vs) != len(inner_validators):
                return ValidationLevel.NONE
            r = reduce(
                vl_and,
                map(lambda f, v: f(v), inner_validators, vs),
                ValidationLevel.FULL,
            )
            return ValidationLevel(r) or ValidationLevel.PARTIAL

        return validator

    def create_defaulter(
        self,
        inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        """Create a tuple defaulter from inner defaulters."""
        return lambda: tuple(inner_defaulter() for inner_defaulter in inner_defaulters)

    def create_converter(
        self,
        inner_converters: list[Converter],
        annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        count = len(inner_converters)
        validator = _registry.validator_from_annotation(annotation)

        def converter(value: Any) -> tuple[Any, ...]:
            if len(value) != count:
                raise ConvertingToAnnotationTypeError(
                    f"Could not convert '{value}' of type '{type(value)}' to '{annotation}'. Size"
                    "mismatch."
                )
            if validator(value) == ValidationLevel.FULL:
                return value
            res = tuple(
                inner_converter(v)
                for inner_converter, v in zip(inner_converters, value)
            )
            return res

        return converter


ar.register_processor(tuple, TupleAnnotationEntry())


# Dynamic Containers: list, set
class DynamicContainerAnnotationEntry[T: type](AnnotationEntry):
    """List annotation entry. Provides a validator, defaulter and converter creators for lists."""

    def __init__(self, sequence_type: T) -> NoneType:
        super().__init__()
        self._sequence_type = sequence_type

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        def validator(vs: Any) -> ValidationLevel:
            if not isinstance(vs, self._sequence_type):
                return ValidationLevel.NONE
            r = reduce(vl_and, map(inner_validators[0], vs), ValidationLevel.FULL)
            return ValidationLevel(r) or ValidationLevel.PARTIAL

        return validator

    def create_defaulter(
        self,
        _inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        return self._sequence_type

    def create_converter(
        self,
        inner_converters: list[Converter],
        annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        """Iterable converter creator. Converts all element of the iterable to the correct type."""
        validator = validator_from_annotation(annotation)

        def converter(value: Any) -> T:
            if validator(value) == ValidationLevel.FULL:
                return value
            try:
                return self._sequence_type(map(inner_converters[0], value))
            except Exception as e:
                raise ConvertingToAnnotationTypeError(
                    f"Could not convert '{value}' of type '{type(value)}' to '{annotation}'."
                ) from e

        return converter


ar.register_processor(list, DynamicContainerAnnotationEntry(list))
ar.register_processor(set, DynamicContainerAnnotationEntry(set))


# Egg cracking: Final, ClassVar
class EggCrackingAnnotationEntry(AnnotationEntry):
    """Egg cracking annotation entry. Provides a validator, defaulter and converter creators for egg
    cracking annotations.
    """

    instance: ClassVar[Self | None] = None

    @classmethod
    def __call__(cls, annotation: Annotation, /) -> AnnotationEntry:
        """To avoid wasting resources, we make it a singleton."""
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        return inner_validators[0]

    def create_defaulter(
        self,
        inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        return inner_defaulters[0]

    def create_converter(
        self,
        inner_converters: list[Converter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        return inner_converters[0]


ar.register_processor(Final, EggCrackingAnnotationEntry())
ar.register_processor(ClassVar, EggCrackingAnnotationEntry())


# dict
class DictAnnotationEntry(AnnotationEntry):
    """Dict annotation entry. Provides a validator, defaulter and converter creators for dicts."""

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        def validator(vs: Any) -> ValidationLevel:
            if not isinstance(vs, dict):
                return ValidationLevel.NONE
            keys = reduce(
                vl_and, map(inner_validators[0], vs.keys()), ValidationLevel.FULL
            )
            values = reduce(
                vl_and, map(inner_validators[1], vs.values()), ValidationLevel.FULL
            )
            return ValidationLevel(vl_and(keys, values)) or ValidationLevel.PARTIAL

        return validator

    def create_defaulter(
        self,
        _inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        return dict

    def create_converter(
        self,
        inner_converters: list[Converter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        def converter(value: Any) -> dict[Any, Any]:
            return {
                inner_converters[0](k): inner_converters[1](v) for k, v in value.items()
            }

        return converter


ar.register_processor(dict, DictAnnotationEntry())


# Literal
class LiteralAnnotationEntry(AnnotationEntry):
    """Literal annotation entry. Provides a validator, defaulter and converter creators for literals."""
    def prepare_inner(self, annotation: Annotation, f: Any):
        return get_args(annotation)

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        def validator(v: Any) -> ValidationLevel:
            if v not in inner_validators:
                return ValidationLevel.NONE
            return ValidationLevel.FULL
        return validator

    def create_defaulter(
        self,
        inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        return lambda: inner_defaulters[0]

    def create_converter(
        self,
        inner_converters: list[Converter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        def converter(value: Any) -> Any:
            if value in inner_converters:
                return value
            return inner_converters[0]
        return converter


ar.register_processor(Literal, LiteralAnnotationEntry())


# Callable
class CallableAnnotationEntry(AnnotationEntry):
    """Callable annotation entry. Provides a validator, defaulter and converter creators for
    callables.
    """
    def prepare_inner(self, annotation: Annotation, f: Any):
        args = get_args(annotation)
        match args:
            case tuple():
                return [Ellipsis, f(Any)]
            case (EllipsisType(), ret):
                return [Ellipsis, f(ret)]
            case (list(l), ret):
                return [f(l), f(ret)]
        return args

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        """Create a validator for Callable types."""
        def validator(v: Any) -> ValidationLevel:
            # We can only check if it's callable, not the signature
            if not callable(v):
                return ValidationLevel.NONE
            return ValidationLevel.FULL
        return validator

    def create_defaulter(
        self,
        _inner_defaulters: list[Defaulter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        """Callable types don't have a default value."""
        return NotImplemented

    def create_converter(
        self,
        _inner_converters: list[Converter],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        """Callable types can't be converted."""
        def converter(value: Any) -> Any:
            if not callable(value):
                raise ConvertingToAnnotationTypeError(
                    f"Could not convert '{value}' of type '{type(value)}' to Callable."
                )
            return value
        return converter


# Note: Callable registration is commented out as it's not fully implemented yet.
# Uncomment when ready to support Callable type coercion.
# ar.register_processor(Callable, CallableAnnotationEntry())
