"""
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

from typing import (
    ClassVar,
    Callable,
    Any,
    Union,
    get_origin,
    get_args,
    get_type_hints,
    overload,
)
from types import NoneType, UnionType

from ...abstract.exceptions.traced_exceptions import TracedException


class TypingError(TracedException):
    """General Error for this typing extension."""


class DefaultingAnnotationError(TypingError):
    """Signals an error while attempting to get a default value for an annotation."""


class ConvertingToAnnotationTypeError(TypingError):
    """Signals an error while attempting to convert a value to an annotation type."""


def is_union(annotation: Any) -> bool:
    """Check if an annotation is a union. A union is a Union or UnionType type.

    Args:
        annotation (Any): The annotation to check.

    Returns:
        bool: Whether the annotation is a union.
    """

    o = get_origin(annotation)
    return o is Union or o is UnionType


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


def type_hints_from_dict(annotations: dict[str, Any]) -> dict[str, Any]:
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


def tuple_defaulter(
    *inner_defaulters: Callable[[], Any]
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


def first_in_union_converter(
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
    inner_converters: list[Callable[[Any], Any]], orig: Any
) -> Callable[[Any], Any]:
    """Union converter. Try inner types conversion in order unless the value is already of the type
    of the union.

    Args:
        inner_converters (list[Callable[[Any], Any]]): converters to try.
        orig (Any): original annotation for error messages.

    Returns:
        Callable[[Any], Any]: A function that converts the provided value to
                                the first matching type of the union.

    """
    types = get_args(orig)

    def converter(value: Any) -> Any:
        for t in types:
            if isinstance(value, t):
                return value
        for inner_converter in inner_converters:
            try:
                return inner_converter(value)
            except Exception:  # pylint: disable=broad-except
                ...
        raise ConvertingToAnnotationTypeError(
            f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
        )

    return converter


def tuple_converter(
    inner_converters: list[Callable[[Any], Any]], orig: Any
) -> Callable[[Any], tuple[Any, ...]]:
    """Tuple converter. Converts all element of the iterable to the correct type.

    Args:
        inner_converters (list[Callable[[Any], Any]]): Converters for each element.
        orig (Any): original annotation for error messages.
        count (int): Number of elements in the tuple.

    Returns:
        Callable[[Any], tuple[Any, ...]]: A function that converts the provided value to
                                a tuple with the correct types.
    """

    count = len(inner_converters)

    def converter(value: Any) -> tuple[Any, ...]:
        try:
            res = tuple(
                inner_converter(v)
                for inner_converter, v in zip(inner_converters, value)
            )
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
            ) from e
        if len(res) != count:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'. Size missmatch."
            )
        return res

    return converter


def list_converter(
    inner_converters: list[Callable[[Any], Any]], orig: Any
) -> Callable[[Any], list[Any]]:
    """List converter. Converts all element of the iterable to the correct type.

    Args:
        inner_converters (list[Callable[[Any], Any]]): the converter for each element.
                                                       Should be a list of length 1.
        orig (Any): original annotation for error messages.

    Returns:
        Callable[[Any], list[Any]]: A function that converts the provided value to
                                a list with the correct type.
    """

    def converter(value: Any) -> list[Any]:
        try:
            return list(map(inner_converters[0], value))
        except Exception as e:
            raise ConvertingToAnnotationTypeError(
                f"Could not convert '{value}' of type '{type(value)}' to '{orig}'."
            ) from e

    return converter


type Defaulter = Callable[[], Any]
type Converter = Callable[[Any], Any]


class AnnotationsManager:
    """
    Static class to manage custom annotations managment. This class should not be accessed directly.
    It is subject to change to use instances instead.
    """

    __type_defaulters_register: ClassVar[dict[type, Defaulter]] = {}
    __type_converters_register: ClassVar[dict[type, Converter]] = {}
    __type_defaulter_creators_register: ClassVar[
        dict[type, Callable[[list[Defaulter], Any], Defaulter]]
    ] = {}
    __type_converter_creators_register: ClassVar[
        dict[type, Callable[[list[Converter], Any], Converter]]
    ] = {}

    @classmethod
    def register_custom_type_defaulter[T](
        cls, special_type: type[T], defaulter: Callable[[], T]
    ) -> None:
        """
        Register a custom type defaulter for a specific type. This allows the annotations
        manager to get a default value for the specified type using the provided defaulter function.

        Args:
            special_type (type[T]): The type for which the custom defaulter is registered.
            defaulter (Callable[[], T]): A function that returns a default value for the specified
                                         type.
        """
        cls.__type_defaulters_register[special_type] = defaulter

    @classmethod
    def register_custom_type_converter[T](
        cls, special_type: type[T], caster: Callable[[Any], T]
    ) -> None:
        """
        Register a custom type converter for a specific type. This allows the annotations
        manager to convert values to the specified type using the provided caster function.

        Args:
            special_type (type[T]): The type for which the custom converter is registered.
            caster (Callable[[Any], T]): A function that converts a value to the specified type.
        """
        cls.__type_converters_register[special_type] = caster

    @classmethod
    def register_custom_type_defaulter_creator[T](
        cls,
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
        cls.__type_defaulter_creators_register[special_type] = creator

    @classmethod
    def register_custom_type_converter_creator[T](
        cls,
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
        cls.__type_converter_creators_register[special_type] = creator

    @overload
    @classmethod
    def defaulter_from_annotation(cls, annotation: None) -> Callable[[], None]: ...

    # for some reason pylance has some issue with this one.
    # @overload
    # @classmethod
    # def defaulter_from_annotation[T](
    #     cls, annotation: Optional[T]
    # ) -> Callable[[], None]: ...

    # for some reason pylance has some issue with this one.
    # @overload
    # @classmethod
    # def defaulter_from_annotation[*ts](
    #     cls, annotation: tuple[*ts]
    # ) -> Callable[[], tuple[*ts]]: ...
    @overload
    @classmethod
    def defaulter_from_annotation[T](cls, annotation: type[T]) -> Callable[[], T]: ...
    @overload
    @classmethod
    def defaulter_from_annotation(cls, annotation: Any) -> Callable[[], Any]: ...

    @classmethod
    def defaulter_from_annotation(cls, annotation: Any) -> Callable[[], Any]:
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
        annotation = type_hints_from_dict({"_": annotation})["_"]

        # Absolute prority to custom defaulters.
        if annotation in cls.__type_defaulters_register:
            return cls.__type_defaulters_register[annotation]

        # The default for NoneType is known.
        if annotation is NoneType:
            return NoneType

        # The annotation might still be a composite type. Composites are not types.
        if isinstance(annotation, type):
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

        # Check if there is a custom defaulter creatir for the origin.
        if origin in cls.__type_defaulter_creators_register:
            return cls.__type_defaulter_creators_register[origin](
                [cls.defaulter_from_annotation(arg) for arg in get_args(annotation)],
                annotation,
            )

        # Migth still be a custom defaulter.
        if origin in cls.__type_defaulters_register:
            return cls.__type_defaulters_register[origin]

        # Union is a special case. Yield the default from the first type.
        if is_union(origin):
            # For an optional, always give None as default.
            if is_optional(annotation):
                return NoneType
            # Otherwise, give the default from the first type.
            # The user should always put the type that should be the default first.
            return cls.defaulter_from_annotation(get_args(origin)[0])

        # Tuple is another special case. All its elements must be defaulted.
        if origin is tuple:
            return tuple_defaulter(
                *(cls.defaulter_from_annotation(arg) for arg in get_args(annotation))
            )
        return cls.defaulter_from_annotation(origin)

    @overload
    @classmethod
    def default_from_annotation(cls, annotation: None) -> Callable[[], None]: ...
    @overload
    @classmethod
    def default_from_annotation[*ts](
        cls, annotation: tuple[*ts]
    ) -> Callable[[], tuple[*ts]]: ...
    @overload
    @classmethod
    def default_from_annotation[T](cls, annotation: type[T]) -> Callable[[], T]: ...
    @overload
    @classmethod
    def default_from_annotation(cls, annotation: Any) -> Callable[[], Any]: ...
    @classmethod
    def default_from_annotation(cls, annotation: Any) -> Any:
        """Provides a default value for an annotation.

        Args:
            annotation (Any): The annotation from which to deduce the default value.

        Raises:
            DefaultingAnnotationError: If it fails to deduce the default value.

        Returns:
            Any: The default value for the provided annotation.
        """
        return cls.defaulter_from_annotation(annotation)()

    @classmethod
    def _create_value_to_annotation_converter(
        cls, annotation: Any, first_in_union: bool = False
    ) -> Callable[[Any], Any]:
        # Converts annotation to a type if it was a forward reference string,
        # None to NoneType and replace Annotated[T, ...] with T.
        annotation = type_hints_from_dict({"_": annotation})["_"]

        # Absolute prority to custom converters.
        if annotation in cls.__type_converters_register:
            return cls.__type_converters_register[annotation]

        # Converted to None is known.
        if annotation is NoneType:
            return none_converter

        # If it is a type, use it as a converter.
        if isinstance(annotation, type):
            return type_converter(annotation)

        origin = get_origin(annotation)
        if origin is None:
            # Something went wrong, we raise.
            raise ConvertingToAnnotationTypeError(
                f"Could not deduce converter from annotation: '{annotation}'."
            )

        # Check if is is a custom converter creator.
        if origin in cls.__type_converter_creators_register:
            return cls.__type_converter_creators_register[origin](
                [
                    cls._create_value_to_annotation_converter(arg)
                    for arg in get_args(annotation)
                ],
                annotation,
            )

        # Might still be a custom converter.
        if origin in cls.__type_converters_register:
            return cls.__type_converters_register[origin]

        # Union is a special case.
        if is_union(origin):
            creator = first_in_union_converter if first_in_union else union_converter
            return creator(
                [
                    cls._create_value_to_annotation_converter(arg)
                    for arg in get_args(annotation)
                ],
                annotation,
            )

        # Note: Further special cases could be added to the __custom_type_converter_creators_register.

        # Tuple is another special case.
        if origin is tuple:
            return tuple_converter(
                [
                    cls._create_value_to_annotation_converter(arg)
                    for arg in get_args(annotation)
                ],
                annotation,
            )

        # List is another special case.
        if origin is list:
            return list_converter(
                [
                    cls._create_value_to_annotation_converter(arg)
                    for arg in get_args(annotation)
                ],
                annotation,
            )

        # Try to use origin as annotation.
        return cls._create_value_to_annotation_converter(origin)

    @classmethod
    def create_value_to_annotation_converter(
        cls, annotation: Any, first_in_union: bool = False
    ) -> Callable[[Any], Any]:
        """Provides a callable that converts a value to the provided annotation.
            The resulting callable will do all in its power to convert the provided value
            to match the type described by the provided annotation or throw an exception.
            Ex.:
              - Only None can be converted to NoneType, everything else will throw.
              - int | str will try to convert to int and then to str if int failed.
              - tuple[int, int, str] will try to convert to tuple[int, int, str].

        Args:
            annotation (Any): the annotation to convert to.

        Raises:
            ConvertingToAnnotationTypeError: _description_

        Returns:
            Callable[[Any], Any]: _description_
        """
        conv = cls._create_value_to_annotation_converter(annotation, first_in_union)

        def converter(value: Any) -> Any:
            try:
                return conv(value)
            except Exception as e:
                raise ConvertingToAnnotationTypeError(
                    f"Could not convert '{value}' of type '{type(value)}' to '{annotation}'."
                ) from e

        return converter

    @classmethod
    def convert_value_to_annotation(
        cls, value: Any, annotation: Any, first_in_union: bool = False
    ) -> Any:
        """Converts a value to the provided annotation. See create_value_to_annotation_converter.

        Args:
            value (Any): the value to convert.
            annotation (Any): the annotation to convert to.

        Returns:
            Any: the value converted to the provided annotation.
        """
        return cls.create_value_to_annotation_converter(annotation, first_in_union)(
            value
        )


def get_annotations_manager() -> type[AnnotationsManager]:
    """Returns the annotations manager."""
    return AnnotationsManager
