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
from abc import abstractmethod, ABC
from types import NoneType, UnionType, NotImplementedType
from typing import (
    Self,
    Iterable,
    Any,
    Callable,
    Union,
    Final,
    ClassVar,
    Literal,
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


type Annotation = Any

type Validator = Callable[[Any], bool] | Callable[[Any], ValidationLevel]
type Defaulter = Callable[[], Any]
type Converter = Callable[[Any], Any]

type ValidatorCreator = Callable[[list[Validator], Annotation], Validator]
type DefaulterCreator = Callable[[list[Defaulter], Annotation], Defaulter]
type ConverterCreator = Callable[[list[Converter], Annotation], Converter]


def is_union(annotation: Annotation) -> bool:
    """Check if an annotation is a union. A union is a Union or UnionType type.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is a union.
    """
    o = get_origin(annotation) or annotation
    return o in (Union, UnionType)


def is_optional(annotation: Annotation) -> bool:
    """Check if an annotation is an optional. An optional is a Union with NoneType.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is an optional.
    """
    return is_union(annotation) and NoneType in get_args(annotation)


def is_binary_optional(annotation: Annotation) -> bool:
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


def resolve_annotation_types(annotations: dict[str, Any]) -> dict[str, Annotation]:
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


def union_validator(inner_validators: list[Validator], _: Any) -> Validator:
    """Create a union validator from inner validators."""

    def validator(v: Any) -> ValidationLevel:
        r = reduce(_vl_or, map(lambda f: f(v), inner_validators), ValidationLevel.NONE)
        if r & ValidationLevel.FULL:
            return ValidationLevel.FULL
        if r & ValidationLevel.PARTIAL:
            return ValidationLevel.PARTIAL
        return ValidationLevel.NONE

    return validator


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
    inner_converters: list[Converter], orig: Annotation
) -> Converter:
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


def union_converter(inner_converters: list[Converter], orig: Any) -> Converter:
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


class AnnotationProcessor:
    """Base class to hold all the processor, and processor creator for an annotation."""

    validate: Validator | None = None
    default: Defaulter | None = None
    convert: Converter | None = None

    def create_validator(
        self,
        inner_validators: list[Validator],
        annotation: Annotation,
        /,
    ) -> Validator | NotImplementedType:
        """Create a validator for the annotation.

        Args:
            inner_validators (list[Validator]): The inner validators.
            annotation (Annotation): The complete annotation to create the validator for.

        Returns:
            Validator: The validator.
        """
        _ = inner_validators, annotation
        return NotImplemented

    def create_defaulter(
        self, inner_defaulter: list[Defaulter], annotation: Annotation, /
    ) -> Defaulter | NotImplementedType:
        """Create a defaulter for the annotation.

        Args:
            inner_defaulter (list[Defaulter]): The inner defaulters.
            annotation (Annotation): The complete annotation to create the defaulter for.

        Returns:
            Defaulter: The defaulter.
        """
        _ = inner_defaulter, annotation
        return NotImplemented

    def create_converter(
        self, inner_converters: list[Converter], annotation: Annotation, /
    ) -> Converter | NotImplementedType:
        """Create a converter for the annotation.

        Args:
            inner_converters (list[Converter]): The inner converters.
            annotation (Annotation): The complete annotation to create the converter for.

        Returns:
            Converter: The converter.
        """
        _ = inner_converters, annotation
        return NotImplemented


class HousingAnnotationProcessor(AnnotationProcessor):
    """House annotation processors given as independent callables."""

    def __init__(
        self,
        validator: Validator | None = None,
        defaulter: Defaulter | None = None,
        converter: Converter | None = None,
        validator_creator: ValidatorCreator | None = None,
        defaulter_creator: DefaulterCreator | None = None,
        converter_creator: ConverterCreator | None = None,
    ):
        self.validate = validator or self.validate
        self.default = defaulter or self.default
        self.convert = converter or self.convert
        self.create_validator = validator_creator or self.create_validator
        self.create_defaulter = defaulter_creator or self.create_defaulter
        self.create_converter = converter_creator or self.create_converter

    def set_validator(self, validator: Validator) -> Self:
        """Set the validator for the annotation processor.
           Can be used as a decorator.

        Args:
            validator (Validator): The validator to set.

        Returns:
            Self: The annotation processor.
        """
        self.validate = validator
        return self

    def set_defaulter(self, defaulter: Defaulter) -> Self:
        """Set the defaulter for the annotation processor.
           Can be used as a decorator.

        Args:
            defaulter (Defaulter): The defaulter to set.

        Returns:
            Self: The annotation processor.
        """
        self.default = defaulter
        return self

    def set_converter(self, converter: Converter) -> Self:
        """Set the converter for the annotation processor.
           Can be used as a decorator.

        Args:
            converter (Converter): The converter to set.

        Returns:
            Self: The annotation processor.
        """
        self.convert = converter
        return self

    def set_validator_creator(self, validator_creator: ValidatorCreator) -> Self:
        """Set the validator creator for the annotation processor.
           Can be used as a decorator.

        Args:
            validator_creator (ValidatorCreator): The validator creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_validator = validator_creator
        return self

    def set_defaulter_creator(self, defaulter_creator: DefaulterCreator) -> Self:
        """Set the defaulter creator for the annotation processor.
           Can be used as a decorator.

        Args:
            defaulter_creator (DefaulterCreator): The defaulter creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_defaulter = defaulter_creator
        return self

    def set_converter_creator(self, converter_creator: ConverterCreator) -> Self:
        """Set the converter creator for the annotation processor.
           Can be used as a decorator.

        Args:
            converter_creator (ConverterCreator): The converter creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_converter = converter_creator
        return self

    @classmethod
    def from_processor(cls, processor: AnnotationProcessor | None) -> Self:
        """Create a HousingAnnotationProcessor from an AnnotationProcessor."""
        if not processor:
            return cls()
        return cls(
            validator=processor.validate,
            defaulter=processor.default,
            converter=processor.convert,
            validator_creator=processor.create_validator,
            defaulter_creator=processor.create_defaulter,
            converter_creator=processor.create_converter,
        )


class AnnotationsProcessor:
    """
    A class to hold all the processors, and processor creator for annotations. It allows
    customization.
    """

    __processors: dict[Annotation, AnnotationProcessor]

    def __init__(self) -> NoneType:
        self.__validators = {}
        self.__defaulters = {}
        self.__converters = {}
        self.__validator_creators = {}
        self.__defaulter_creators = {}
        self.__converter_creators = {}

    def register_processor(
        self, annotation: Annotation, processor: AnnotationProcessor
    ) -> None:
        """
        Register a custom type processor for a specific type. This allows the annotations
        processor to process values for the specified type using the provided processor.

        Args:
            special_type (type): The type for which the custom processor is registered.
            processor (AnnotationProcessor): The processor to use for the specified type.
        """
        self.__processors[annotation] = processor

    def _register_single_processor(
        self, annotation: Annotation, s_processor: Any, setter: Any
    ) -> None:
        processor = self.__processors.get(annotation)
        if not isinstance(processor, HousingAnnotationProcessor):
            processor = HousingAnnotationProcessor.from_processor(processor)
            self.__processors[annotation] = processor
        setter(processor, s_processor)

        # Invalidate caches
        # TODO

    def register_validator(self, annotation: Annotation, validator: Validator) -> None:
        """
        Register a custom type validator for a specific type. This allows the annotations
        processor to validate values against the specified type using the provided validator
        function.

        Returning a ValidationLevel with the validator allows for more fine-grained control. For
        example, the validator can return ValidationLevel.PARTIAL if you have a tuple("1", "2")
        to convert to Union[list[int], tuple[int, int]] so that it can be converted to tuple(1, 2)
        instead of [1, 2].

        Args:
            annotation (Annotation): The type for which the custom validator is registered.
            validator (Validator): A function that returns True if the value is valid for the
                                            specified type.
        """
        return self._register_single_processor(
            annotation, validator, HousingAnnotationProcessor.set_validator
        )

    def register_defaulter(
        self, annotation: Annotation, defaulter: Defaulter
    ) -> None:
        """
        Register a custom type defaulter for a specific type. This allows the annotations
        processor to get a default value for the specified type using the provided defaulter
        function.

        Args:
            annotation (Annotation): The type for which the custom defaulter is registered.
            defaulter (Defaulter): A function that returns a default value for the specified
                                            type.
        """
        return self._register_single_processor(
            annotation, defaulter, HousingAnnotationProcessor.set_defaulter
        )

    def register_converter(
        self, annotation: Annotation, converter: Converter
    ) -> None:
        """
        Register a custom type converter for a specific type. This allows the annotations
        processor to convert values to the specified type using the provided caster function.

        Args:
            annotation (Annotation): The type for which the custom converter is registered.
            converter (Converter): A function that converts a value to the specified type.
        """
        return self._register_single_processor(
            annotation, converter, HousingAnnotationProcessor.set_converter
        )

    def register_validator_creator(
        self,
        annotation: Annotation,
        creator: ValidatorCreator,
    ) -> None:
        """
        Register a custom type validator creator for a specific type. This allows the annotations
        processor to create validators for the specified type using the provided creator function.

        The creator function will receive a list containing a list of validators for each inner type
        as well as the original annotation.

        Args:
            annotation (Annotation): The type for which the custom validator creator is registered.
            creator (ValidatorCreator):
                    A function that creates a validator function for the specified type.
        """
        self._register_single_processor(
            annotation, creator, HousingAnnotationProcessor.set_validator_creator
        )

    def register_defaulter_creator(
        self,
        annotation: Annotation,
        creator: DefaulterCreator,
    ) -> None:
        """
        Register a custom type defaulter creator for a specific type. This allows the annotations
        processor to create defaulter for the specified type using the provided creator function.

        The creator function will receive a list containing a list of defaulter for each inner type
        as well as the original annotation.

        Args:
            annotation (Annotation): The type for which the custom defaulter creator is registered.
            creator (DefaulterCreator):
                    A function that creates a defaulter function for the specified type.
        """
        self._register_single_processor(
            annotation, creator, HousingAnnotationProcessor.set_defaulter_creator
        )

    def register_converter_creator(
        self,
        annotation: Annotation,
        creator: ConverterCreator,
    ) -> None:
        """
        Register a custom type converter creator for a specific type. This allows the annotations
        processor to create converters for the specified type using the provided creator function.

        The creator function will receive a list containing a list of converter for each inner type
        as well as the original annotation.

        Args:
            annotation (Annotation): The type for which the custom converter creator is registered.
            creator (ConverterCreator):
                A function that creates a converter function for the specified type.
        """
        self._register_single_processor(
            annotation, creator, HousingAnnotationProcessor.set_converter_creator
        )

    def get_processor(self, annotation: Annotation) -> AnnotationProcessor:
        """Get the processor for a specified annotation.

        Args:
            annotation (Annotation): The annotation for which to get the processor.

        Returns:
            AnnotationProcessor: The processor for the specified annotation.
        """
        if annotation not in self.__processors:
            raise KeyError(f"No processor registered for annotation {annotation}.")
        return self.__processors[annotation]

    def has_processor(self, annotation: Annotation) -> bool:
        """Check if a processor is registered for a specific annotation.

        Args:
            annotation (Annotation): The annotation for which to check if a processor is registered.

        Returns:
            bool: True if a processor is registered for the specified annotation, False otherwise.
        """
        return annotation in self.__processors


    def list_registered_types(self) ->list[Annotation]:
        """Get all registered types for debugging/introspection."""
        return list(self.__processors.keys())


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

    # Egg cracking type wrappers are special cases.
    if origin in {Final, ClassVar}:
        return validator_from_annotation(get_args(annotation)[0])

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

    # Egg cracking type wrappers are special cases.
    if origin in {Final, ClassVar}:
        return defaulter_from_annotation(get_args(annotation)[0])

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

    # Egg cracking type wrappers are special cases.
    if origin in {Final, ClassVar}:
        return _create_value_to_annotation_converter(
            get_args(annotation)[0], first_in_union
        )

    # Note: Further special cases could be added to the __custom_type_converter_creators_register.

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


# Register a few known types

tr = type_registry()


def create_tuple_validator(inner_validators: list[Validator], _: Any) -> Validator:
    """Create a tuple validator from inner validators."""

    def validator(vs: Any) -> ValidationLevel:
        if not isinstance(vs, tuple) or len(vs) != len(inner_validators):  # type: ignore
            return ValidationLevel.NONE
        r = reduce(
            _vl_and, map(lambda f, v: f(v), inner_validators, vs), ValidationLevel.FULL  # type: ignore
        )
        return ValidationLevel(r) or ValidationLevel.PARTIAL

    return validator


def iterable_validator_creator_from_type[T](
    it_type: type[Iterable[T]],
) -> Callable[[list[Validator], Any], Validator]:
    """Create a iterable validator creator from inner validators."""

    def inner(inner_validators: list[Validator], _: Any) -> Validator:
        def validator(vs: Any) -> ValidationLevel:
            if not isinstance(vs, it_type):
                return ValidationLevel.NONE
            r = reduce(
                _vl_and, map(inner_validators[0], vs), ValidationLevel.FULL  # type: ignore
            )
            return ValidationLevel(r) or ValidationLevel.PARTIAL

        return validator

    return inner


def create_tuple_defaulter(
    inner_defaulters: list[Defaulter], _: Any
) -> Callable[[], tuple[Any, ...]]:
    """Create a tuple defaulter from inner defaulters."""
    return lambda: tuple(inner_defaulter() for inner_defaulter in inner_defaulters)


def create_tuple_converter(
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


def iterable_converter_creator_from_type[T](
    it_type: type[T],
) -> Callable[[list[Converter], Any], Converter]:
    """Iterable converter creator. Converts all element of the iterable to the correct type."""

    def inner(inner_converters: list[Converter], orig: Any) -> Callable[[Any], T]:
        validator = validator_from_annotation(orig)

        def converter(value: Any) -> T:
            if validator(value) == ValidationLevel.FULL:
                return value
            try:
                return it_type(map(inner_converters[0], value))  # type: ignore
            except Exception as e:
                raise ConvertingToAnnotationTypeError(
                    f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
                ) from e

        return converter

    return inner


# tuple
tr.register_validator_creator(tuple, create_tuple_validator)
tr.register_defaulter_creator(tuple, create_tuple_defaulter)
tr.register_converter_creator(tuple, create_tuple_converter)

# list
tr.register_validator_creator(list, iterable_validator_creator_from_type(list))
tr.register_converter_creator(list, iterable_converter_creator_from_type(list))

# set
tr.register_validator_creator(set, iterable_validator_creator_from_type(set))
tr.register_converter_creator(set, iterable_converter_creator_from_type(set))

# dict

# TODO: dict, Callable, Literal, See also for constants to not coerce if annotations does not know how.
