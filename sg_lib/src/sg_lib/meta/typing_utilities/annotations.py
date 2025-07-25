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
Description: This module provides tools to manage annotations and types. This includes:
            - Various free functions: is_union, is_optional, is_binary_optional,
              type_hints_from_dict
            - The annotations manager that provides tools to create default values from annotations
                and convert values to annotations. The convertions and defaulting can be extended
                with custom converters and defaulters. See register_custom_type_defaulter,
                register_custom_type_converter and register_custom_type_converter_creator
🦙
"""


__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from enum import IntEnum
from functools import lru_cache, reduce
from types import NoneType, UnionType
from typing import (
    Iterable,
    Any,
    Callable,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from ...abstract.exceptions.traced_exceptions import TracedException


class TypingError(TracedException):
    """General Error for this typing extension."""


class DefaultingAnnotationError(TypingError):
    """Signals an error while attempting to get a default value for an annotation."""


class ConvertingToAnnotationTypeError(TypingError):
    """Signals an error while attempting to convert a value to an annotation type."""


class ValidationLevel(IntEnum):
    """Validation level for type checking.

    NONE: No validation. The value does not match the annotation.
    FULL: The value matches the annotation.
    PARTIAL: The value matches the top level annotation. For example, [1, "2"] matches partialy
        list[str] because it is a list but it does not contains only strings. ("1", "2") does not
        match because it is not a list.
    """

    NONE = 0
    FULL = 1
    PARTIAL = 2


def _vl_and(vl1: int, vl2: int) -> int:
    return int(vl1) & int(vl2)


def _vl_or(vl1: int, vl2: int) -> int:
    return int(vl1) | int(vl2)


type Validator = Callable[[Any], bool] | Callable[[Any], ValidationLevel]
type Defaulter = Callable[[], Any]
type Converter = Callable[[Any], Any]

def is_union(annotation: Any) -> bool:
    """Check if an annotation is a union. A union is a Union or UnionType type.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is a union.
    """
    o = get_origin(annotation) or annotation
    return o in (Union, UnionType)


def is_optional(annotation: Any) -> bool:
    """Check if an annotation is an optional. An optional is a Union with NoneType.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is an optional.
    """
    return is_union(annotation) and NoneType in get_args(annotation)


def is_binary_optional(annotation: Any) -> bool:
    """Check if an annotation is a binary optional. A binary optional is a Union with NoneType and
    a single other type.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is an optional.
    """
    if not is_union(annotation):
        return False
    args = get_args(annotation)
    return len(args) == 2 and NoneType in args


def resolve_annotation_types(annotations: dict[str, Any]) -> dict[str, Any]:
    """
    Get type hints from a dictionary of annotations. See typing.get_type_hints.

    This function is useful when you want to get the type hints from a dictionary
    of annotations instead of a class or a function.

    Args:
        annotations (dict[str, Any]): A dictionary of annotations.

    Returns:
        dict[str, Any]: A dictionary of type hints.
    """
    X = type("X", (), {"__annotations__": annotations})
    return get_type_hints(X)

def union_validator(
    inner_validators: list[Validator], _: Any
) -> Validator:
    """Create a union validator from inner validators."""
    def validator(v: Any) -> ValidationLevel:
        r = reduce(_vl_or, map(lambda f: f(v), inner_validators), ValidationLevel.NONE)
        if r & ValidationLevel.FULL:
            return ValidationLevel.FULL
        if r & ValidationLevel.PARTIAL:
            return ValidationLevel.PARTIAL
        return ValidationLevel.NONE

    return validator

def tuple_validator(
    inner_validators: list[Validator], _: Any
) -> Validator:
    """Create a tuple validator from inner validators."""
    def validator(vs: Any) -> ValidationLevel:
        if not isinstance(vs, tuple) or len(vs) != len(inner_validators):  # type: ignore
            return ValidationLevel.NONE
        r = reduce(
            _vl_and, map(lambda f, v: f(v), inner_validators, vs), ValidationLevel.FULL  # type: ignore
        )
        return ValidationLevel(r) or ValidationLevel.PARTIAL

    return validator


def iterable_validator_from_type[T](
    it_type: type[Iterable[T]], inner_validators: list[Validator], _: Any
) -> Validator:
    """Create a iterable validator creator from inner validators."""
    def validator(vs: Any) -> ValidationLevel:
        if not isinstance(vs, it_type):
            return ValidationLevel.NONE
        r = reduce(
            _vl_and, map(inner_validators[0], vs), ValidationLevel.FULL  # type: ignore
        )
        return ValidationLevel(r) or ValidationLevel.PARTIAL

    return validator


def list_validator(
    inner_validators: list[Validator], _: Any
) -> Validator:
    """Create a list validator from an inner validator."""
    return iterable_validator_from_type(list, inner_validators, _)


def tuple_defaulter(
    inner_defaulters: list[Defaulter], _: Any
) -> Callable[[], tuple[Any, ...]]:
    """Create a tuple defaulter from inner defaulters."""
    return lambda: tuple(inner_defaulter() for inner_defaulter in inner_defaulters)


def none_converter(value: Any) -> None:
    """Convert a value to None. Raises an error if the value is not None.

    Args:
        value (Any): the value to convert.

    Raises:
        ConvertingToAnnotationTypeError: Raised if the value is not None.

    Returns:
        _type_: Always returns None
    """
    if value is not None:
        raise ConvertingToAnnotationTypeError(
            f"Could not convert '{value}' of type '{type(value)}' to 'None'."
        )
    return None


def type_converter[T](c_type: type[T]) -> Callable[[Any], T]:
    """Create a type converter for a specific type.

    Args:
        c_type (type[T]): the type to convert to.

    Returns:
        Callable[[Any], T]: A function that converts a value to the specified type.
    """

    def converter(value: Any) -> T:
        if isinstance(value, c_type):
            return value
        try:
            return c_type(value)  # type: ignore
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{c_type}'."
            ) from e

    return converter


def strict_union_converter(
    inner_converters: list[Callable[[Any], Any]], orig: Any
) -> Callable[[Any], Any]:
    """Union converter. Converts the provided value to the first type of the union or raises an
    error.

    Args:
        inner_converters (list[Callable[[Any], Any]]): converters to try.
        orig (Any): original annotation for error messages.

    Returns:
        Callable[[Any], Any]: A function that converts the provided value to
                                the first matching type of the union.

    """

    def converter(value: Any) -> Any:
        try:
            return inner_converters[0](value)
        except Exception as e:  # pylint: disable=broad-except
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to first type of '{orig}'."
            ) from e

    return converter


def union_converter(
    inner_converters: list[Converter], orig: Any
) -> Converter:
    """Union converter. Try inner types conversion in order unless the value is already of a type
    of the union. Partial matches are tested first.

    Args:
        inner_converters (list[Converter]): converters to try.
        orig (Any): original annotation for error messages.

    Returns:
        Converter: A function that converts the provided value to
                                the first matching type of the union.

    """
    validators = list(map(validator_from_annotation, get_args(orig)))

    def converter(value: Any) -> Any:
        partials: list[Converter] = []
        others: list[Converter] = []
        for validator, inner_converter in zip(validators, inner_converters):
            match ValidationLevel(validator(value)):
                case ValidationLevel.NONE:
                    others.append(inner_converter)
                case ValidationLevel.FULL:
                    return value
                case ValidationLevel.PARTIAL:
                    partials.append(inner_converter)

        for inner_converter in partials + others:
            try:
                return inner_converter(value)
            except Exception:  # pylint: disable=broad-except
                ...
        raise ConvertingToAnnotationTypeError(
            f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
        )

    return converter


def tuple_converter(
    inner_converters: list[Converter], orig: Any
) -> Callable[[Any], tuple[Any, ...]]:
    """Tuple converter. Converts all element of the iterable to the correct type.

    Args:
        inner_converters (list[Converter]): Converters for each element.
        orig (Any): original annotation for error messages.
        count (int): Number of elements in the tuple.

    Returns:
        Callable[[Any], tuple[Any, ...]]: A function that converts the provided value to
                                a tuple with the correct types.
    """

    count = len(inner_converters)
    validator = validator_from_annotation(orig)

    def converter(value: Any) -> tuple[Any, ...]:
        if len(value) != count:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'. Size mismatch."
            )
        if validator(value) == ValidationLevel.FULL:
            return value
        try:
            res = tuple(
                inner_converter(v)
                for inner_converter, v in zip(inner_converters, value)
            )
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
            ) from e
        return res

    return converter


def list_converter(
    inner_converters: list[Converter], orig: Any
) -> Callable[[Any], list[Any]]:
    """List converter. Converts all element of the iterable to the correct type.

    Args:
        inner_converters (list[Converter]): the converter for each element.
                                                       Should be a list of length 1.
        orig (Any): original annotation for error messages.

    Returns:
        Callable[[Any], list[Any]]: A function that converts the provided value to
                                a list with the correct type.
    """
    validator = validator_from_annotation(orig)

    def converter(value: Any) -> list[Any]:
        if validator(value) == ValidationLevel.FULL:
            return value
        try:
            return list(map(inner_converters[0], value))
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
            ) from e

    return converter


class TypeRegistry:
    """
    Static class to add custom type behavior to the annotations validation, defaulting and
    conversion.
    """

    __validators: dict[type, Validator]
    __defaulters: dict[type, Defaulter]
    __converters: dict[type, Converter]
    __validator_creators: dict[type, Callable[[list[Validator], Any], Validator]]
    __defaulter_creators: dict[type, Callable[[list[Defaulter], Any], Defaulter]]
    __converter_creators: dict[type, Callable[[list[Converter], Any], Converter]]

    def __init__(self) -> NoneType:
        self.__validators = {}
        self.__defaulters = {}
        self.__converters = {}
        self.__validator_creators = {}
        self.__defaulter_creators = {}
        self.__converter_creators = {}

    def register_validator(self, special_type: type, validator: Validator) -> None:
        """
        Register a custom type validator for a specific type. This allows the annotations
        manager to validate values against the specified type using the provided validator function.

        Returning a ValidationLevel with the validator allows for more fine-grained control. For
        example, the validator can return ValidationLevel.PARTIAL if you have a tuple("1", "2")
        to convert to Union[list[int], tuple[int, int]] so that it can be converted to tuple(1, 2)
        instead of [1, 2].

        Args:
            special_type (type): The type for which the custom validator is registered.
            validator (Validator): A function that returns True if the value is valid for the
                                            specified type.
        """
        self.__validators[special_type] = validator

        # Invalidate caches
        validator_from_annotation.cache_clear()

    def register_defaulter[T](
        self, special_type: type[T], defaulter: Callable[[], T]
    ) -> None:
        """
        Register a custom type defaulter for a specific type. This allows the annotations
        manager to get a default value for the specified type using the provided defaulter function.

        Args:
            special_type (type[T]): The type for which the custom defaulter is registered.
            defaulter (Callable[[], T]): A function that returns a default value for the specified
                                            type.
        """
        self.__defaulters[special_type] = defaulter

        # Invalidate caches
        defaulter_from_annotation.cache_clear()

    def register_converter[T](
        self, special_type: type[T], caster: Callable[[Any], T]
    ) -> None:
        """
        Register a custom type converter for a specific type. This allows the annotations
        manager to convert values to the specified type using the provided caster function.

        Args:
            special_type (type[T]): The type for which the custom converter is registered.
            caster (Callable[[Any], T]): A function that converts a value to the specified type.
        """
        self.__converters[special_type] = caster

        # Invalidate caches
        converter_from_annotation.cache_clear()

    def register_validator_creator[T](
        self,
        special_type: type[T],
        creator: Callable[[list[Validator], Any], Callable[[Any], bool]],
    ) -> None:
        """
        Register a custom type validator creator for a specific type. This allows the annotations
        manager to create validators for the specified type using the provided creator function.

        The creator function will receive a list containing a list of validators for each inner type
        as well as the original annotation.

        Args:
            special_type (type[T]): The type for which the custom validator creator is registered.
            creator (Callable[[list[Validator], Any], Callable[[Any], bool]]):
                    A function that creates a validator function for the specified type.
        """
        self.__validator_creators[special_type] = creator

        # Invalidate caches
        validator_from_annotation.cache_clear()

    def register_defaulter_creator[T](
        self,
        special_type: type[T],
        creator: Callable[[list[Defaulter], Any], Callable[[], T]],
    ) -> None:
        """
        Register a custom type defaulter creator for a specific type. This allows the annotations
        manager to create defaulter for the specified type using the provided creator function.

        The creator function will receive a list containing a list of defaulter for each inner type
        as well as the original annotation.

        Args:
            special_type (type[T]): The type for which the custom defaulter creator is registered.
            creator (Callable[[list[Defaulter], Any], Callable[[], T]]):
                    A function that creates a defaulter function for the specified type.
        """
        self.__defaulter_creators[special_type] = creator

        # Invalidate caches
        defaulter_from_annotation.cache_clear()

    def register_converter_creator[T](
        self,
        special_type: type[T],
        creator: Callable[[list[Converter], Any], Callable[[Any], T]],
    ) -> None:
        """
        Register a custom type converter creator for a specific type. This allows the annotations
        manager to create converters for the specified type using the provided creator function.

        The creator function will receive a list containing a list of converter for each inner type
        as well as the original annotation.

        Args:
            special_type (type[T]): The type for which the custom converter creator is registered.
            creator (Callable[[list[Converter], Any], Callable[[Any], T]]):
                A function that creates a converter function for the specified type.
        """
        self.__converter_creators[special_type] = creator

        # Invalidate caches
        converter_from_annotation.cache_clear()

    def unregister_validator(self, special_type: type) -> None:
        """Unregister a custom type validator for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom validator.
        """
        self.__validators.pop(special_type, None)

    def unregister_defaulter(self, special_type: type) -> None:
        """Unregister a custom type defaulter for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom defaulter.
        """
        self.__defaulters.pop(special_type, None)

    def unregister_converter(self, special_type: type) -> None:
        """Unregister a custom type converter for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom converter.
        """
        self.__converters.pop(special_type, None)

    def unregister_validator_creator(self, special_type: type) -> None:
        """Unregister a custom type validator creator for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom validator creator.
        """
        self.__validator_creators.pop(special_type, None)

    def unregister_defaulter_creator(self, special_type: type) -> None:
        """Unregister a custom type defaulter creator for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom defaulter creator.
        """
        self.__defaulter_creators.pop(special_type, None)

    def unregister_converter_creator(self, special_type: type) -> None:
        """Unregister a custom type converter creator for a specific type.

        Args:
            special_type (type): The type for which to unregister the custom converter creator.
        """
        self.__converter_creators.pop(special_type, None)

    def get_validator(self, special_type: type) -> Validator:
        """Get the validator for a specific type.

        Args:
            special_type (type): The type for which to get the validator.

        Returns:
            Validator: The validator function for the specified type.
        """
        if special_type not in self.__validators:
            raise KeyError(f"No validator registered for type {special_type}.")
        return self.__validators[special_type]

    def get_defaulter(self, special_type: type) -> Defaulter:
        """Get the defaulter for a specific type.

        Args:
            special_type (type): The type for which to get the defaulter.

        Returns:
            Defaulter: The defaulter function for the specified type.
        """
        if special_type not in self.__defaulters:
            raise KeyError(f"No defaulter registered for type {special_type}.")
        return self.__defaulters[special_type]

    def get_converter(self, special_type: type) -> Converter:
        """Get the converter for a specific type.

        Args:
            special_type (type): The type for which to get the converter.

        Returns:
            Converter: The converter function for the specified type.
        """
        if special_type not in self.__converters:
            raise KeyError(f"No converter registered for type {special_type}.")
        return self.__converters[special_type]

    def get_validator_creator(
        self, special_type: type
    ) -> Callable[[list[Validator], Any], Validator]:
        """Get the validator creator for a specific type.

        Args:
            special_type (type): The type for which to get the validator creator.

        Returns:
            Callable[[list[Validator], Any], Validator]: The validator creator function for the
                                                         specified type.
        """
        if special_type not in self.__validator_creators:
            raise KeyError(f"No validator creator registered for type {special_type}.")
        return self.__validator_creators[special_type]

    def get_defaulter_creator(
        self, special_type: type
    ) -> Callable[[list[Defaulter], Any], Defaulter]:
        """Get the defaulter creator for a specific type.

        Args:
            special_type (type): The type for which to get the defaulter creator.

        Returns:
            Callable[[list[Defaulter], Any], Defaulter]: The defaulter creator function for the
                                                         specified type.
        """
        if special_type not in self.__defaulter_creators:
            raise KeyError(f"No defaulter creator registered for type {special_type}.")
        return self.__defaulter_creators[special_type]

    def get_converter_creator(
        self, special_type: type
    ) -> Callable[[list[Converter], Any], Converter]:
        """Get the converter creator for a specific type.

        Args:
            special_type (type): The type for which to get the converter creator.

        Returns:
            Callable[[list[Converter], Any], Converter]: The converter creator function for the
                                                         specified type.
        """
        if special_type not in self.__converter_creators:
            raise KeyError(f"No converter creator registered for type {special_type}.")
        return self.__converter_creators[special_type]

    def has_validator(self, special_type: type) -> bool:
        """Check if a validator is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a validator is registered.

        Returns:
            bool: True if a validator is registered for the specified type, False otherwise.
        """
        return special_type in self.__validators

    def has_defaulter(self, special_type: type) -> bool:
        """Check if a defaulter is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a defaulter is registered.

        Returns:
            bool: True if a defaulter is registered for the specified type, False otherwise.
        """
        return special_type in self.__defaulters

    def has_converter(self, special_type: type) -> bool:
        """Check if a converter is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a converter is registered.

        Returns:
            bool: True if a converter is registered for the specified type, False otherwise.
        """
        return special_type in self.__converters

    def has_validator_creator(self, special_type: type) -> bool:
        """Check if a validator creator is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a validator creator is registered.

        Returns:
            bool: True if a validator creator is registered for the specified type, False otherwise.
        """
        return special_type in self.__validator_creators

    def has_defaulter_creator(self, special_type: type) -> bool:
        """Check if a defaulter creator is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a defaulter creator is registered.

        Returns:
            bool: True if a defaulter creator is registered for the specified type, False otherwise.
        """
        return special_type in self.__defaulter_creators

    def has_converter_creator(self, special_type: type) -> bool:
        """Check if a converter creator is registered for a specific type.

        Args:
            special_type (type): The type for which to check if a converter creator is registered.

        Returns:
            bool: True if a converter creator is registered for the specified type, False otherwise.
        """
        return special_type in self.__converter_creators

    def list_registered_types(self) -> dict[str, list[type]]:
        """Get all registered types for debugging/introspection."""
        return {
            "validators": list(self.__validators.keys()),
            "defaulters": list(self.__defaulters.keys()),
            "converters": list(self.__converters.keys()),
            "validator_creators": list(self.__validator_creators.keys()),
            "defaulter_creators": list(self.__defaulter_creators.keys()),
            "converter_creators": list(self.__converter_creators.keys()),
        }


@lru_cache(1)
def type_registry() -> TypeRegistry:
    """Type registry singleton. Allows to register
    custom type defaulters and converters.

    Args:

    Returns:
        TypeRegistry: the type registry instance.
    """
    return TypeRegistry()

@lru_cache(128)
def validator_from_annotation(annotation: Any) -> Validator:
    """Provides a callable that validates an annotation.

    Args:
        annotation (Any): The annotation to validate.

    Returns:
        Validator: The validator function for the provided annotation.
    """
    # Converts annotation to a type if it was a forward reference string,
    # None to NoneType and replace Annotated[T, ...] with T.
    annotation = resolve_annotation_types({"_": annotation})["_"]

    tr = type_registry()

    # The annotation might still be a composite type. Composites are not types.
    if isinstance(annotation, type):
        # Absolute prority to registry validators.
        if tr.has_validator(annotation):
            return tr.get_validator(annotation)

        # Otherwise, just check if it is an instance of the annotation.
        return lambda v: isinstance(v, annotation)

    # Retrieve the origin of the annotation. Ex.: Union[int, str] -> Union
    origin = get_origin(annotation)
    if origin is None:
        # Something went wrong, we raise.
        raise DefaultingAnnotationError(
            f"Could not deduce validator from annotation: {annotation}."
        )

    # Check if there is a custom validator creator for the origin.
    if tr.has_validator_creator(origin):
        return tr.get_validator_creator(origin)(
            [validator_from_annotation(arg) for arg in get_args(annotation)],
            annotation,
        )

    # Migth still be a custom validator. That was not detected before because it was obfuscated
    # as an annotation.
    if tr.has_validator(origin):
        return tr.get_validator(origin)

    # Union is a special case.
    if is_union(origin):
        return union_validator(
            [validator_from_annotation(arg) for arg in get_args(annotation)],
            annotation,
        )

    # Tuple is another special case. All its elements must be validated with a specific validator.
    if origin is tuple:
        return tuple_validator(
            [validator_from_annotation(arg) for arg in get_args(annotation)],
            annotation,
        )

    if origin is list:
        return list_validator(
            [validator_from_annotation(arg) for arg in get_args(annotation)],
            annotation,
        )
    return validator_from_annotation(origin)

@overload
@lru_cache(128)
def defaulter_from_annotation(annotation: None) -> Callable[[], None]: ...
@overload
@lru_cache(128)
def defaulter_from_annotation[*ts](
    annotation: tuple[*ts],
) -> Callable[[], tuple[*ts]]: ...
@overload
@lru_cache(128)
def defaulter_from_annotation[T](annotation: type[T]) -> Callable[[], T]: ...
@overload
@lru_cache(128)
def defaulter_from_annotation(annotation: Any) -> Callable[[], Any]: ...


@lru_cache(128)
def defaulter_from_annotation(annotation: Any) -> Callable[[], Any]:
    """Provides a callable that returns a default value for an annotation.

    Args:
        annotation (Any): The annotation from which to deduce the default value.

    Raises:
        DefaultingAnnotationError: If it fails to deduce the default value.

    Returns:
        Callable[[], Any]: The defaulter function for the provided annotation.
    """
    # Converts annotation to a type if it was a forward reference string,
    # None to NoneType and replace Annotated[T, ...] with T.
    annotation = resolve_annotation_types({"_": annotation})["_"]

    tr = type_registry()

    # The annotation might still be a composite type. Composites are not types.
    if isinstance(annotation, type):
        # Absolute prority to registry defaulters.
        if tr.has_defaulter(annotation):
            return tr.get_defaulter(annotation)

        # The default for NoneType is known.
        if annotation is NoneType:
            return NoneType

        try:
            annotation()  # ensure it is a valid default call.
            return annotation
        except Exception as e:
            raise DefaultingAnnotationError(
                f"Could not deduce defaulter from annotation: {annotation}"
            ) from e

    # Retrieve the origin of the annotation. Ex.: Union[int, str] -> Union
    origin = get_origin(annotation)
    if origin is None:
        # Something went wrong, we raise.
        raise DefaultingAnnotationError(
            f"Could not deduce defaulter from annotation: {annotation}"
        )

    # Check if there is a custom defaulter creator for the origin.
    if tr.has_defaulter_creator(origin):
        return tr.get_defaulter_creator(origin)(
            [defaulter_from_annotation(arg) for arg in get_args(annotation)],
            annotation,
        )

    # Migth still be a custom defaulter. That was not detected before because it was obfuscated
    # as an annotation.
    if tr.has_defaulter(origin):
        return tr.get_defaulter(origin)

    # Union is a special case. Yield the default from the first type.
    if is_union(origin):
        # For an optional, always give None as default.
        if is_optional(annotation):
            return NoneType
        # Otherwise, give the default from the first type.
        # The user should always put the type that should be the default first.
        return defaulter_from_annotation(get_args(annotation)[0])  # type: ignore todo: fix

    # Tuple is another special case. All its elements must be defaulted.
    if origin is tuple:
        return tuple_defaulter(
            [defaulter_from_annotation(arg) for arg in get_args(annotation)],  # type: ignore todo: fix
            annotation,
        )
    return defaulter_from_annotation(origin)  # type: ignore todo: fix


@overload
def default_from_annotation(annotation: None) -> Callable[[], None]: ...
@overload
def default_from_annotation[*ts](
    annotation: tuple[*ts],
) -> Callable[[], tuple[*ts]]: ...
@overload
def default_from_annotation[T](annotation: type[T]) -> Callable[[], T]: ...
@overload
def default_from_annotation(annotation: Any) -> Callable[[], Any]: ...


# Cannot cache this function because we might return mutable objects.
def default_from_annotation(annotation: Any) -> Any:
    """Provides a default value for an annotation.

    Args:
        annotation (Any): The annotation from which to deduce the default value.

    Raises:
        DefaultingAnnotationError: If it fails to deduce the default value.

    Returns:
        Any: The default value for the provided annotation.
    """
    return defaulter_from_annotation(annotation)()  # type: ignore todo: fix


def _create_value_to_annotation_converter(
    annotation: Any, first_in_union: bool = False
) -> Converter:
    # Converts annotation to a type if it was a forward reference string,
    # None to NoneType and replace Annotated[T, ...] with T.
    annotation = resolve_annotation_types({"_": annotation})["_"]

    tr = type_registry()

    if isinstance(annotation, type):
        # Absolute prority to registry converters.
        if tr.has_converter(annotation):
            return tr.get_converter(annotation)

        # Converted to None is known.
        if annotation is NoneType:
            return none_converter

        # If it is another type, use it as a converter.
        return type_converter(annotation)

    origin = get_origin(annotation)
    if origin is None:
        # Something went wrong, we raise.
        raise ConvertingToAnnotationTypeError(
            f"Could not deduce converter from annotation: '{annotation}'."
        )

    # Check if is is a custom converter creator.
    if tr.has_converter_creator(origin):
        return tr.get_converter_creator(origin)(
            [
                _create_value_to_annotation_converter(arg, first_in_union)
                for arg in get_args(annotation)
            ],
            annotation,
        )

    # Might still be a custom converter. That was not detected before because it was obfuscated
    # as an annotation.
    if tr.has_converter(origin):
        return tr.get_converter(origin)

    # Union is a special case.
    if is_union(origin):
        creator = strict_union_converter if first_in_union else union_converter
        return creator(
            [
                _create_value_to_annotation_converter(arg, first_in_union)
                for arg in get_args(annotation)
            ],
            annotation,
        )

    # Note: Further special cases could be added to the __custom_type_converter_creators_register.

    # Tuple is another special case.
    if origin is tuple:
        return tuple_converter(
            [
                _create_value_to_annotation_converter(arg, first_in_union)
                for arg in get_args(annotation)
            ],
            annotation,
        )

    # List is another special case.
    if origin is list:
        return list_converter(
            [
                _create_value_to_annotation_converter(arg, first_in_union)
                for arg in get_args(annotation)
            ],
            annotation,
        )

    # Try to use origin as annotation.
    return _create_value_to_annotation_converter(origin, first_in_union)


@lru_cache(128)
def converter_from_annotation(
    annotation: Any, first_in_union: bool = False
) -> Converter:
    """Provides a callable that converts a value to the provided annotation.
        The resulting callable will do all in its power to convert the provided value
        to match the type described by the provided annotation or throw an exception.
        Ex.:
            - Only None can be converted to NoneType, everything else will throw.
            - int | str will try to convert to int and then to str if int failed.
            - tuple[int, int, str] will try to convert to tuple[int, int, str].

    Args:
        annotation (Any): the annotation to convert to.
        first_in_union (bool, optional): If True, the converter will try to convert to
        the first type in the union. Defaults to False. When False, the converter requires
        a validator for each involved type.

    Raises:
        ConvertingToAnnotationTypeError: _description_

    Returns:
        Callable[[Any], Any]: _description_
    """
    conv = _create_value_to_annotation_converter(annotation, first_in_union)

    def converter(value: Any) -> Any:
        try:
            return conv(value)
        except TypingError as e:
            raise e
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{annotation}'."
                "An Exception was raised."
            ) from e

    return converter


# Cannot cache this function because we might return mutable objects.
def convert_value_to_annotation(
    value: Any, annotation: Any, first_in_union: bool = False
) -> Any:
    """Converts a value to the provided annotation. See create_value_to_annotation_converter.

    Args:
        value (Any): the value to convert.
        annotation (Any): the annotation to convert to.
        first_in_union (bool, optional): If True, the converter will try to convert to
        the first type in the union. Defaults to False. When False, the converter requires
        a validator for each involved type.

    Returns:
        Any: the value converted to the provided annotation.
    """
    return converter_from_annotation(annotation, first_in_union)(value)
