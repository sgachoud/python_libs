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

from __future__ import annotations

from functools import reduce
from types import EllipsisType, NotImplementedType, NoneType
from typing import Self, Any, Callable, ClassVar, Final, Literal, TYPE_CHECKING, get_args

from ..exceptions import ConvertingToAnnotationTypeError
from ..typing import Annotation
from ._entries import AnnotationEntry
from ._types import CastType, Converter, Defaulter, ValidationLevel, Validator, vl_and

if TYPE_CHECKING:
    from ._registry import AnnotationsRegistry

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




# tuple
class TupleAnnotationEntry(AnnotationEntry):
    """Tuple annotation entry. Provides a validator, defaulter and converter creators for tuples."""

    def raw_create_defaulter(
        self, annotation: Annotation, registry: AnnotationsRegistry, /
    ) -> Defaulter | NotImplementedType:
        """A variadic tuple defaults to empty without defaulting its element type."""
        args = get_args(annotation)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple
        return super().raw_create_defaulter(annotation, registry)

    def prepare_inner(self, annotation: Annotation, f: Callable[[Any], Any]) -> Any:
        """The ellipsis in a variadic tuple repeats its element annotation."""
        args = get_args(annotation)
        if len(args) == 2 and args[1] is Ellipsis:
            return [f(args[0])]
        return super().prepare_inner(annotation, f)

    def create_validator(
        self,
        inner_validators: list[Validator],
        _annotation: Annotation,
        _registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        """Create a tuple validator from inner validators."""
        args = get_args(_annotation)
        variadic = len(args) == 2 and args[1] is Ellipsis

        def validator(vs: Any) -> ValidationLevel:
            if not isinstance(vs, tuple):
                return ValidationLevel.NONE
            if variadic:
                r = reduce(vl_and, map(inner_validators[0], vs), ValidationLevel.FULL)
                return ValidationLevel(r) or ValidationLevel.PARTIAL
            if len(vs) != len(inner_validators):
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
        args = get_args(annotation)
        variadic = len(args) == 2 and args[1] is Ellipsis
        validator = _registry.validator_from_annotation(annotation)

        def converter(value: Any) -> tuple[Any, ...]:
            if variadic:
                if validator(value) == ValidationLevel.FULL:
                    return value
                try:
                    return tuple(map(inner_converters[0], value))
                except Exception as error:
                    raise ConvertingToAnnotationTypeError(
                        f"Could not convert {value!r} to '{annotation}'."
                    ) from error
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




# Dynamic Containers: list, set
class DynamicContainerAnnotationEntry[T: type](AnnotationEntry):
    """List annotation entry. Provides a validator, defaulter and converter creators for lists."""

    def __init__(self, sequence_type: T) -> NoneType:
        super().__init__()
        self._sequence_type = sequence_type

    def raw_create_defaulter(
        self, annotation: Annotation, registry: AnnotationsRegistry, /
    ) -> Defaulter | NotImplementedType:
        """An empty container does not require a default for its element type."""
        return self.create_defaulter([], annotation, registry)

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
        validator = _registry.validator_from_annotation(annotation)

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




# dict
class DictAnnotationEntry(AnnotationEntry):
    """Dict annotation entry. Provides a validator, defaulter and converter creators for dicts."""

    def raw_create_defaulter(
        self, annotation: Annotation, registry: AnnotationsRegistry, /
    ) -> Defaulter | NotImplementedType:
        """An empty dictionary needs neither key nor value defaults."""
        return self.create_defaulter([], annotation, registry)

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




# Literal
class LiteralAnnotationEntry(AnnotationEntry):
    """Literal annotation entry. Provides a validator, defaulter and converter creators for literals.

    Matching uses Python equality, including True == 1. Conversion preserves a
    matching input; otherwise it returns the first literal, also used as the default.
    """
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



def register_builtins(registry: AnnotationsRegistry) -> None:
    """Install a fresh set of built-in handlers on a registry."""
    registry.register_processor(CastType, CastTypeAnnotationEntry())
    registry.register_processor(Any, AnyAnnotationEntry())
    registry.register_processor(tuple, TupleAnnotationEntry())
    registry.register_processor(list, DynamicContainerAnnotationEntry(list))
    registry.register_processor(set, DynamicContainerAnnotationEntry(set))
    registry.register_processor(Final, EggCrackingAnnotationEntry())
    registry.register_processor(ClassVar, EggCrackingAnnotationEntry())
    registry.register_processor(dict, DictAnnotationEntry())
    registry.register_processor(Literal, LiteralAnnotationEntry())
