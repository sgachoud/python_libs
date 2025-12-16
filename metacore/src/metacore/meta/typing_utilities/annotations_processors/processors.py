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

from __future__ import annotations

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from enum import IntEnum
from functools import lru_cache, reduce
from types import NoneType, NotImplementedType
from typing import (
    DefaultDict,
    Generator,
    Self,
    Any,
    Callable,
    get_args,
    get_origin,
)


from .errors import (
    TypingError,
    AnnotationProcessorError,
    ConvertingToAnnotationTypeError,
    DefaultingAnnotationError,
)
from ..utilities import resolve_annotation_types, is_union, is_optional


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


def vl_and(vl1: int, vl2: int) -> int:
    """Logical and between two validation levels with a cast to int."""
    return int(vl1) & int(vl2)


def vl_or(vl1: int, vl2: int) -> int:
    """Logical or between two validation levels with a cast to int."""
    return int(vl1) | int(vl2)


type Annotation = Any

type Validator = Callable[[Any], bool] | Callable[[Any], ValidationLevel]
type Defaulter = Callable[[], Any]
type Converter = Callable[[Any], Any]

type ValidatorCreator = Callable[..., Validator]
type DefaulterCreator = Callable[..., Defaulter]
type ConverterCreator = Callable[..., Converter]


def union_validator(inner_validators: Generator[Validator], _: Any) -> Validator:
    """Create a union validator from inner validators."""
    inner_validators_list = list(inner_validators)
    def validator(v: Any) -> ValidationLevel:
        r = reduce(vl_or, map(lambda f: f(v), inner_validators_list), ValidationLevel.NONE)
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


def union_converter(
    inner_converters: Generator[Converter],
    orig: Annotation,
    registry: AnnotationsRegistery,
) -> Converter:
    """Union converter. Try inner types conversion in order unless the value is already of a type
    of the union. Partial matches are tested first.

    Args:
        inner_converters (Generator[Converter]): converters to try.
        orig (Any): original annotation for error messages.

    Returns:
        Converter: A function that converts the provided value to
                                the first matching type of the union.

    """
    validators = list(map(registry.validator_from_annotation, get_args(orig)))
    # Convert generator to list to avoid exhaustion on multiple calls
    converters_list = list(inner_converters)

    def converter(value: Any) -> Any:
        partials: list[Converter] = []
        others: list[Converter] = []
        for validator, inner_converter in zip(validators, converters_list):
            match ValidationLevel(validator(value)):
                case ValidationLevel.NONE:
                    others.append(inner_converter)
                case ValidationLevel.FULL:
                    return inner_converter(value)
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


class AnnotationEntry:
    """Base class to hold all the processor, and processor creator for an annotation."""

    validate: Validator | None = None
    default: Defaulter | None = None
    convert: Converter | None = None

    def _prepare_inner_safe(
        self, annotation: Annotation, f: Callable[[Any], Any], p_name: str
    ) -> Any:
        try:
            return self.prepare_inner(annotation, f)
        except TypingError as e:
            raise AnnotationProcessorError(
                f"Could not create {p_name} for annotation '{annotation}'."
            ) from e

    def prepare_inner(self, annotation: Annotation, f: Callable[[Any], Any]) -> Any:
        """Can be overriden to change how the inner annotations are processed."""
        return list(map(f, get_args(annotation)))

    def raw_create_validator(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Validator | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_validator to avoid creating inner validators.

        Args:
            annotation (Annotation): The annotation to create the validator for.
            registry (AnnotationsRegistery): The registry to use.

        Returns:
            Validator | NotImplementedType: The validator for the annotation, or NotImplemented.
        """
        return self.create_validator(
            self._prepare_inner_safe(
                annotation, registry.validator_from_annotation, "validator"
            ),
            annotation,
            registry,
        )

    def raw_create_defaulter(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Defaulter | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_defaulter to avoid creating inner defaulters.

        Args:
            annotation (Annotation): The annotation to create the defaulter for.
            registry (AnnotationsRegistery): The registry to use.

        Returns:
            Defaulter | NotImplementedType: The defaulter for the annotation, or NotImplemented.
        """
        return self.create_defaulter(
            self._prepare_inner_safe(
                annotation, registry.defaulter_from_annotation, "defaulter"
            ),
            annotation,
            registry,
        )

    def raw_create_converter(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Defaulter | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_converter to avoid creating inner converters.

        Args:
            annotation (Annotation): The annotation to create the converter for.
            registry (AnnotationsRegistery): The registry to use.

        Returns:
            Converter | NotImplementedType: The converter for the annotation, or NotImplemented.
        """
        return self.create_converter(
            self._prepare_inner_safe(
                annotation, registry.converter_from_annotation, "converter"
            ),
            annotation,
            registry,
        )

    def create_validator(
        self,
        inner_validators: list[Validator],
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Validator | NotImplementedType:
        """Create a validator for the annotation.

        Args:
            inner_validators (list[Validator]): The inner validators.
            annotation (Annotation): The complete annotation to create the validator for.

        Returns:
            Validator: The validator.
        """
        _ = inner_validators, annotation, registry
        return NotImplemented

    def create_defaulter(
        self,
        inner_defaulter: list[Defaulter],
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Defaulter | NotImplementedType:
        """Create a defaulter for the annotation.

        Args:
            inner_defaulter (list[Defaulter]): The inner defaulters.
            annotation (Annotation): The complete annotation to create the defaulter for.

        Returns:
            Defaulter: The defaulter.
        """
        _ = inner_defaulter, annotation, registry
        return NotImplemented

    def create_converter(
        self,
        inner_converters: list[Converter],
        annotation: Annotation,
        registry: AnnotationsRegistery,
        /,
    ) -> Converter | NotImplementedType:
        """Create a converter for the annotation.

        Args:
            inner_converters (list[Converter]): The inner converters.
            annotation (Annotation): The complete annotation to create the converter for.

        Returns:
            Converter: The converter.
        """
        _ = inner_converters, annotation, registry
        return NotImplemented


class HousingAnnotationEntry(AnnotationEntry):
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
    def from_processor(cls, processor: AnnotationEntry | None) -> Self:
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


class AnnotationsRegistery:
    """
    A class to hold all the processors, and processors creator for annotations. It allows
    customization.
    """

    class CacheEntry:
        """
        A cache entry to store the validator, defaulter and converter of an annotation.
        """

        def __init__(
            self,
            validator: Validator | None = None,
            defaulter: Defaulter | None = None,
            converter: Converter | None = None,
        ) -> NoneType:
            self.validator = validator
            self.defaulter = defaulter
            self.converter = converter

    __processors: dict[Annotation, AnnotationEntry]
    __cache: DefaultDict[Annotation, CacheEntry]

    def __init__(self) -> NoneType:
        self.__processors = {}
        self.__cache = DefaultDict(self.CacheEntry)

    def clear_validator_cache_for_annotation(self, annotation: Annotation) -> None:
        """Clear the validator cache for a specific annotation.

        Args:
            annotation (Annotation): The annotation to clear the validator cache for.
        """
        if annotation in self.__cache:
            self.__cache[annotation].validator = None
        annotation = resolve_annotation_types({"_": annotation})["_"]
        if annotation in self.__cache:
            self.__cache[annotation].validator = None

    def clear_defaulter_cache_for_annotation(self, annotation: Annotation) -> None:
        """Clear the defaulter cache for a specific annotation.

        Args:
            annotation (Annotation): The annotation to clear the defaulter cache for.
        """
        if annotation in self.__cache:
            self.__cache[annotation].defaulter = None
        annotation = resolve_annotation_types({"_": annotation})["_"]
        if annotation in self.__cache:
            self.__cache[annotation].defaulter = None

    def clear_converter_cache_for_annotation(self, annotation: Annotation) -> None:
        """Clear the converter cache for a specific annotation.

        Args:
            annotation (Annotation): The annotation to clear the converter cache for.
        """
        if annotation in self.__cache:
            self.__cache[annotation].converter = None
        annotation = resolve_annotation_types({"_": annotation})["_"]
        if annotation in self.__cache:
            self.__cache[annotation].converter = None

    def clear_cache_for_annotation(self, annotation: Annotation) -> None:
        """Clear the cache for a specific annotation.

        Args:
            annotation (Annotation): The annotation to clear the cache for.
        """
        if annotation in self.__cache:
            del self.__cache[annotation]
        annotation = resolve_annotation_types({"_": annotation})["_"]
        if annotation in self.__cache:
            del self.__cache[annotation]

    def clear_cache(self) -> None:
        """Clear the cache of all annotations. Removes all cached processors."""
        self.__cache.clear()

    def register_processor(
        self, annotation: Annotation, processor: AnnotationEntry
    ) -> None:
        """
        Register a custom type processor for a specific type. This allows the annotations
        processor to process values for the specified type using the provided processor.

        Args:
            special_type (type): The type for which the custom processor is registered.
            processor (AnnotationProcessor): The processor to use for the specified type.
        """
        self.__processors[annotation] = processor
        self.clear_cache_for_annotation(annotation)

    def _register_single_processor(
        self, annotation: Annotation, s_processor: Any, setter: Any
    ) -> None:
        processor = self.__processors.get(annotation)
        if not isinstance(processor, HousingAnnotationEntry):
            processor = HousingAnnotationEntry.from_processor(processor)
            self.register_processor(annotation, processor)
        else:
            self.clear_cache_for_annotation(annotation)
        setter(processor, s_processor)

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
            annotation, validator, HousingAnnotationEntry.set_validator
        )

    def register_defaulter(self, annotation: Annotation, defaulter: Defaulter) -> None:
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
            annotation, defaulter, HousingAnnotationEntry.set_defaulter
        )

    def register_converter(self, annotation: Annotation, converter: Converter) -> None:
        """
        Register a custom type converter for a specific type. This allows the annotations
        processor to convert values to the specified type using the provided caster function.

        Args:
            annotation (Annotation): The type for which the custom converter is registered.
            converter (Converter): A function that converts a value to the specified type.
        """
        return self._register_single_processor(
            annotation, converter, HousingAnnotationEntry.set_converter
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
            annotation, creator, HousingAnnotationEntry.set_validator_creator
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
            annotation, creator, HousingAnnotationEntry.set_defaulter_creator
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
            annotation, creator, HousingAnnotationEntry.set_converter_creator
        )

    def get_processor(self, annotation: Annotation) -> AnnotationEntry | None:
        """Get the processor for a specified annotation.

        Args:
            annotation (Annotation): The annotation for which to get the processor.

        Returns:
            AnnotationProcessor: The processor for the specified annotation or None if no
            processor is registered.
        """
        return self.__processors.get(annotation)

    def has_processor(self, annotation: Annotation) -> bool:
        """Check if a processor is registered for a specific annotation.

        Args:
            annotation (Annotation): The annotation for which to check if a processor is registered.

        Returns:
            bool: True if a processor is registered for the specified annotation, False otherwise.
        """
        return annotation in self.__processors

    def list_registered_types(self) -> list[Annotation]:
        """Get all registered types for debugging/introspection."""
        return list(self.__processors.keys())

    def __validator_from_annotation(self, annotation: Annotation) -> Validator:
        """Get the validator for a specific annotation. If a cached value exists, it is returned.

        Args:
            annotation (Annotation): The annotation for which to get the validator. This should be
            a resolved annotation.

        Returns:
            Validator: The validator, for the specified annotation.
        """

        cache_entry = self.__cache[annotation]
        if cache_entry.validator:
            return cache_entry.validator

        entry = self.get_processor(annotation)

        # Absolute prority to registered validator.
        if entry and entry.validate:
            return entry.validate

        # The annotation might still be a composite type. Composites are not types.
        if isinstance(annotation, type):
            # For the validator just checks if it is an instance of the annotation.
            return lambda v: isinstance(v, annotation)

        # Retrieve the origin of the annotation. Ex.: Union[int, str] -> Union
        origin = get_origin(annotation)
        if origin is None:
            # Something went wrong, we raise for missing validator.
            raise AnnotationProcessorError(
                f"Could not deduce validator from annotation: {annotation}. Not a type and no"
                " origin found."
            )

        origin_entry = self.get_processor(origin)
        if origin_entry:
            # Check if there are valid custom creators for the origin.
            inner_validators = (
                self.__validator_from_annotation(arg) for arg in get_args(annotation)
            )

            validator = origin_entry.raw_create_validator(annotation, self)
            if validator is not NotImplemented:
                return validator

            # Migth still be a custom processor. That was not detected before because it was
            # obfuscated as an annotation.
            if origin_entry.validate:
                return origin_entry.validate

        # Union is a special case.
        if is_union(origin):
            # Check if there are valid custom creators for the origin.
            inner_validators = (
                self.__validator_from_annotation(arg) for arg in get_args(annotation)
            )
            return union_validator(inner_validators, annotation)

        return self.__validator_from_annotation(origin)

    def __defaulter_from_annotation(self, annotation: Annotation) -> Defaulter:
        """Get the defaulter for a specific annotation.

        Args:
            annotation (Annotation): The annotation for which to get the defaulter. This should be
            a resolved annotation.

        Returns:
            Defaulter: The defaulter for the specified annotation.
        """

        cache_entry = self.__cache[annotation]
        if cache_entry.defaulter:
            return cache_entry.defaulter

        entry = self.get_processor(annotation)

        # Absolute prority to registered processors.
        if entry and entry.default:
            return entry.default

        # The annotation might still be a composite type. Composites are not types.
        if isinstance(annotation, type):

            # For the defaulter.
            try:
                # ensure it is a valid default call.
                annotation()
                return annotation
            except TypeError as e:
                # otherwise, raise on request of a defaulter.
                raise DefaultingAnnotationError(
                    f"Could not deduce defaulter from annotation: {annotation}."
                    " {annotation}() is not a valid default call."
                ) from e

        # Retrieve the origin of the annotation. Ex.: Union[int, str] -> Union
        origin = get_origin(annotation)
        if origin is None:
            # Something went wrong, we raise for missing defaulter.
            raise AnnotationProcessorError(
                f"Could not deduce defaulter from annotation: {annotation}. Not a type and no"
                " origin found."
            )

        origin_entry = self.get_processor(origin)
        if origin_entry:
            # Check if there are valid custom creators for the origin.
            inner_defaulters = (
                self.__defaulter_from_annotation(arg) for arg in get_args(annotation)
            )

            defaulter = origin_entry.raw_create_defaulter(annotation, self)
            if defaulter is not NotImplemented:
                return defaulter

            # Migth still be a custom defaulter. That was not detected before because it was
            # obfuscated as an annotation.
            if origin_entry.default:
                return origin_entry.default

        # Union is a special case.
        if is_union(origin):
            # Check if there are valid custom creators for the origin.
            inner_defaulters = (
                self.__defaulter_from_annotation(arg) for arg in get_args(annotation)
            )
            # For an optional, always give None as defaulter.
            if is_optional(annotation):
                return NoneType
            # Otherwise, give the default from the first type.
            # The user should always put the type that should be the default first.
            return next(inner_defaulters)

        return self.__defaulter_from_annotation(origin)

    def __converter_from_annotation(self, annotation: Annotation) -> Converter:
        """Get the converter for a specific annotation.

        Args:
            annotation (Annotation): The annotation for which to get the converter.

        Returns:
            Converter: The converter for the specified annotation.
        """

        cache_entry = self.__cache[annotation]
        if cache_entry.converter:
            return cache_entry.converter

        entry = self.get_processor(annotation)

        # Absolute prority to registered processors.
        if entry and entry.convert:
            return entry.convert

        # The annotation might still be a composite type. Composites are not types.
        if isinstance(annotation, type):
            # For the converter uses the type as a converter.
            return type_converter(annotation)

        # Retrieve the origin of the annotation. Ex.: Union[int, str] -> Union
        origin = get_origin(annotation)
        if origin is None:
            # Something went wrong, we raise for missing processors.
            raise AnnotationProcessorError(
                f"Could not deduce converter from annotation: {annotation}. Not a type and no"
                " origin found."
            )

        origin_entry = self.get_processor(origin)
        if origin_entry:
            # Check if there are valid custom creators for the origin.
            inner_converters = (
                self.__converter_from_annotation(arg) for arg in get_args(annotation)
            )

            converter = origin_entry.raw_create_converter(annotation, self)
            if converter is not NotImplemented:
                return converter

            # Migth still be a custom processor. That was not detected before because it was
            # obfuscated as an annotation.
            if origin_entry.convert:
                return origin_entry.convert

        # Union is a special case.
        if is_union(origin):
            # Check if there are valid custom creators for the origin.
            inner_converters = (
                self.__converter_from_annotation(arg) for arg in get_args(annotation)
            )
            return union_converter(inner_converters, annotation, self)

        return self.__converter_from_annotation(origin)

    def processors_from_annotation(
        self, annotation: Annotation
    ) -> tuple[Validator | Exception, Defaulter | Exception, Converter | Exception]:
        """Get the validator, defaulter and converter for a specific annotation.

        Args:
            annotation (Annotation): The annotation for which to get the validator, defaulter and
                converter.

        Returns:
            tuple[Validator | Exception, Defaulter | Exception, Converter | Exception]: The
                validator, defaulter and converter for the specified annotation.
        """
        annotation = resolve_annotation_types({"_": annotation})["_"]
        try:
            v = self.__validator_from_annotation(annotation)
        except TypingError as e:
            v = e
        try:
            d = self.__defaulter_from_annotation(annotation)
        except TypingError as e:
            d = e
        try:
            c = self.__converter_from_annotation(annotation)
        except TypingError as e:
            c = e

        return v, d, c

    def validator_from_annotation(self, annotation: Annotation) -> Validator:
        """Provides a callable that validates a value with an annotation. If one of the type in the
        annotation if not known, an error is raised.

        Note that the validation knowledge of the annotation registry can be extended
        with custom validators. See AnnotationRegistery.register_processor,
        AnnotationRegistery.register_validator and AnnotationRegistery.register_validator_creator.

        For example to validate a tuple(int, str, float) you can use:
            >>> validator = validator_from_annotation(tuple[int, str, float])
            >>> print(validator((1, "2", 3.0))) # True
            >>> print(validator((1, "2", "3.0"))) # False

        Args:
            annotation (Any): The annotation to validate.

        Returns:
            Validator: The validator function for the provided annotation.
        """
        annotation = resolve_annotation_types({"_": annotation})["_"]
        return self.__validator_from_annotation(annotation)

    def defaulter_from_annotation(self, annotation: Annotation) -> Defaulter:
        """Provides a callable that defaults an annotation. If one of the type in the annotation
        if not known, an error is raised.

        Note that the defaulting knowledge of the annotation registry can be extended
        with custom defaulters. See AnnotationRegistery.register_processor,
        AnnotationRegistery.register_defaulter and AnnotationRegistery.register_defaulter_creator.

        For example to default a tuple(int, str, float) you can use:
            >>> defaulter = defaulter_from_annotation(tuple[int, str, float])
            >>> print(defaulter((1, "2", 3.0))) # (0, "", 0.0)

        Args:
            annotation (Any): The annotation to defaulter.

        Returns:
            Defaulter: The defaulter function for the provided annotation.
        """
        annotation = resolve_annotation_types({"_": annotation})["_"]
        return self.__defaulter_from_annotation(annotation)

    def converter_from_annotation(self, annotation: Annotation) -> Converter:
        """Provides a callable that converts a value to an annotation. If one of the type in the
        annotation if not known, an error is raised. When called, the function will raise a
        ConvertingToAnnotationTypeError if the provided value cannot be converted.

        Note that the convertion knowledge of the annotation registry can be extended
        with custom converters. See AnnotationRegistery.register_processor,
        AnnotationRegistery.register_converter and AnnotationRegistery.register_converter_creator.

        For example to convert a value to tuple(int, str, float) you can use:
            >>> converter = converter_from_annotation(tuple[int, str, float])
            >>> print(converter((1, "2", 3.0))) # (1, "2", 3.0)
            >>> print(converter((1.0, 2, "3.0"))) # (1, "2", 3.0)
            >>> print(converter((1, 2))) # ConvertingToAnnotationTypeError

        If first_in_union is True, the converter will always convert to the first type in the union.
            >>> converter = converter(str | int, first_in_union=True)
            >>> print(converter("42")) # '42'
            >>> print(converter(42)) # '42'
        Otherwise, if the type is in the union, the value will be kept as is.
            >>> converter = converter(str | int)
            >>> print(converter("42")) # '42'
            >>> print(converter(42)) # 42

        Args:
            annotation (Any): The annotation to convert.
            first_in_union (bool): If true, force conversion to the first type in the union.

        Returns:
            Converter: The converter function for the provided annotation.
        """
        annotation = resolve_annotation_types({"_": annotation})["_"]
        return self.__converter_from_annotation(annotation)

    def validate_with_annotation(
        self, annotation: Annotation, value: Any
    ) -> bool | ValidationLevel:
        """This function is a shortcut to self.validator_from_annotation(annotation)(value)."""
        return self.validator_from_annotation(annotation)(value)

    def default_annotation(self, annotation: Annotation) -> Any:
        """This function is a shortcut to self.defaulter_from_annotation(annotation)()."""
        return self.defaulter_from_annotation(annotation)()

    def convert_to_annotation(self, annotation: Annotation, value: Any) -> Any:
        """This function is a shortcut to self.converter_from_annotation(annotation)(value)."""
        return self.converter_from_annotation(annotation)(value)


@lru_cache(1)
def annotation_registry() -> AnnotationsRegistery:
    """Default annotation registry. Allows to register custom type defaulters and converters.
    See AnnotationRegistery for more information.

    Returns:
        TypeRegistry: the type registry instance.
    """
    return AnnotationsRegistery()


def validator_from_annotation(annotation: Annotation) -> Validator:
    """This function is a shortcut to `annotation_registry().validator_from_annotation()`."""
    return annotation_registry().validator_from_annotation(annotation)


def defaulter_from_annotation(annotation: Annotation) -> Defaulter:
    """This function is a shortcut to `annotation_registry().defaulter_from_annotation()`."""
    return annotation_registry().defaulter_from_annotation(annotation)


def validate_from_annotation(
    annotation: Annotation, value: Any
) -> bool | ValidationLevel:
    """This function is a shortcut to `annotation_registry().validate()`."""
    return annotation_registry().validate_with_annotation(annotation, value)


def default_from_annotation(annotation: Annotation) -> Any:
    """This function is a shortcut to `annotation_registry().default()`."""
    return annotation_registry().default_annotation(annotation)


def convert_to_annotation(annotation: Annotation, value: Any) -> Any:
    """This function is a shortcut to `annotation_registry().convert_to_annotation()`."""
    return annotation_registry().convert_to_annotation(annotation, value)
