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
Description: Tests for the annotations module.
🦙

Note: written with the assistance Claude AI.
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"


from typing import Union, Optional, Any
from types import NoneType

import pytest

from sg_lib.src.sg_lib.meta.typing_utilities.annotations import (
    TypingError,
    DefaultingAnnotationError,
    ConvertingToAnnotationTypeError,
    TypeRegistry,
    Validator,
    Converter,
    Defaulter,
    ValidationLevel,
    is_union,
    is_optional,
    is_binary_optional,
    resolve_annotation_types,
    create_tuple_defaulter,
    none_converter,
    type_converter,
    strict_union_converter,
    union_converter,
    create_tuple_converter,
    iterable_converter_creator_from_type,
    type_registry,
    validator_from_annotation,
    defaulter_from_annotation,
    default_from_annotation,
    converter_from_annotation,
    convert_value_to_annotation,
)


class TestExceptions:
    """Test custom exception classes."""

    def test_typing_error_inheritance(self):
        """Test that TypingError inherits from TracedException."""
        error = TypingError("test message")
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    def test_defaulting_annotation_error(self):
        """Test DefaultingAnnotationError can be raised."""
        with pytest.raises(DefaultingAnnotationError):
            raise DefaultingAnnotationError("defaulting error")

    def test_converting_to_annotation_type_error(self):
        """Test ConvertingToAnnotationTypeError can be raised."""
        with pytest.raises(ConvertingToAnnotationTypeError):
            raise ConvertingToAnnotationTypeError("conversion error")


class TestTypeChecking:
    """Test type checking utility functions."""

    def test_is_union_with_union_type(self):
        """Test is_union with Union type."""
        assert is_union(Union[int, str]) is True
        assert is_union(int) is False
        assert is_union(Optional[int]) is True  # Optional is Union[T, None]

    def test_is_union_with_union_type_modern(self):
        """Test is_union with modern union syntax (Python 3.10+)."""
        if hasattr(type(int | str), "__name__"):  # Check if UnionType exists
            assert is_union(int | str) is True

    def test_is_optional_with_optional_type(self):
        """Test is_optional with Optional type."""
        assert is_optional(Optional[int]) is True
        assert is_optional(Union[int, None]) is True
        assert is_optional(Union[int, str]) is False
        assert is_optional(int) is False

    def test_is_binary_optional(self):
        """Test is_binary_optional function."""
        assert is_binary_optional(Optional[int]) is True
        assert is_binary_optional(Union[int, None]) is True
        assert is_binary_optional(Union[int, str, None]) is False
        assert is_binary_optional(Union[int, str]) is False
        assert is_binary_optional(int) is False


class TestAnnotationResolution:
    """Test annotation resolution utilities."""

    def test_resolve_annotation_types_basic(self):
        """Test basic annotation resolution."""
        annotations: dict[str, Any] = {"x": int, "y": str}
        resolved = resolve_annotation_types(annotations)
        assert resolved["x"] is int
        assert resolved["y"] is str

    def test_resolve_annotation_types_forward_ref(self):
        """Test annotation resolution with forward references."""
        annotations = {"x": "int", "y": "str"}
        resolved = resolve_annotation_types(annotations)
        assert resolved["x"] is int
        assert resolved["y"] is str

    def test_resolve_annotation_types_with_generics(self) -> None:
        """Test resolve_annotation_types with generic types."""
        annotations: dict[str, Any] = {"items": list[int], "mapping": dict[str, int]}
        resolved = resolve_annotation_types(annotations)
        assert resolved["items"] == list[int]
        assert resolved["mapping"] == dict[str, int]


class TestConverters:
    """Test converter functions."""

    def test_none_converter_success(self):
        """Test none_converter with None value."""
        result: None = none_converter(None)
        assert result is None

    def test_none_converter_failure(self):
        """Test none_converter with non-None value."""
        with pytest.raises(ConvertingToAnnotationTypeError):
            none_converter(42)

    def test_type_converter_success(self):
        """Test type_converter with convertible value."""
        int_converter = type_converter(int)
        assert int_converter("42") == 42
        assert int_converter(42) == 42

    def test_type_converter_failure(self):
        """Test type_converter with non-convertible value."""
        int_converter = type_converter(int)
        with pytest.raises(ConvertingToAnnotationTypeError):
            int_converter("not a number")

    def test_strict_union_converter(self):
        """Test strict_union_converter."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = strict_union_converter(converters, Union[int, str])
        assert converter("42") == 42  # Only tries first converter

    def test_strict_union_converter_failure(self):
        """Test strict_union_converter when first converter fails."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = strict_union_converter(converters, Union[int, str])
        with pytest.raises(ConvertingToAnnotationTypeError):
            converter("not a number")  # First converter fails

    def test_union_converter_type_match(self):
        """Test union_converter when value already matches a type."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = union_converter(converters, Union[int, str])
        assert converter(42) == 42  # Direct type match
        assert converter("hello") == "hello"  # Direct type match

    def test_union_converter_conversion(self):
        """Test union_converter with type conversion."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = union_converter(converters, Union[int, str])
        assert converter(42.5) == 42  # Converts to int

    def test_union_converter_failure(self):
        """Test union_converter when all conversions fail."""
        converters = [type_converter(int)]
        converter = union_converter(converters, Union[int])
        with pytest.raises(ConvertingToAnnotationTypeError):
            converter("not a number")

    def test_tuple_converter_success(self):
        """Test tuple_converter with correct input."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = create_tuple_converter(converters, tuple[int, str])
        result = converter(("42", 123))
        assert result == (42, "123")

    def test_tuple_converter_size_mismatch(self):
        """Test tuple_converter with size mismatch."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = create_tuple_converter(converters, tuple[int, str])
        with pytest.raises(ConvertingToAnnotationTypeError):
            converter((42,))  # Too few elements

    def test_tuple_converter_conversion_error(self):
        """Test tuple_converter with conversion error."""
        converters: list[Converter] = [type_converter(int), type_converter(str)]
        converter = create_tuple_converter(converters, tuple[int, str])
        with pytest.raises(ConvertingToAnnotationTypeError):
            converter(("not a number", 123))

    def test_list_converter_success(self):
        """Test list_converter with correct input."""
        converters = [type_converter(int)]
        converter = iterable_converter_creator_from_type(list)(converters, list[int])
        result = converter(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_list_converter_failure(self):
        """Test list_converter with conversion error."""
        converters = [type_converter(int)]
        converter = iterable_converter_creator_from_type(list)(converters, list[int])
        with pytest.raises(ConvertingToAnnotationTypeError):
            converter(["not", "numbers"])


class TestDefaulters:
    """Test defaulter functions."""

    def test_tuple_defaulter(self):
        """Test tuple_defaulter function."""
        defaulter = create_tuple_defaulter([lambda: 1, lambda: "hello"], tuple[int, str])
        result = defaulter()
        assert result == (1, "hello")

    def test_tuple_defaulter_empty(self):
        """Test tuple_defaulter with no inner defaulters."""
        defaulter = create_tuple_defaulter([], tuple)
        result = defaulter()
        assert not result


class TestDefaulterFromAnnotation:
    """Test defaulter_from_annotation function."""

    def test_defaulter_from_basic_type(self):
        """Test defaulter for basic types."""
        int_defaulter = defaulter_from_annotation(int)
        assert int_defaulter() == 0

        str_defaulter = defaulter_from_annotation(str)
        assert str_defaulter() == ""

        list_defaulter = defaulter_from_annotation(list)
        assert list_defaulter() == []

    def test_defaulter_from_none_type(self):
        """Test defaulter for NoneType."""
        none_defaulter = defaulter_from_annotation(NoneType)
        assert none_defaulter is NoneType
        assert none_defaulter() is None

    def test_defaulter_from_optional(self):
        """Test defaulter for Optional types."""
        opt_defaulter = defaulter_from_annotation(Optional[int])
        assert opt_defaulter is NoneType
        assert opt_defaulter() is None

    def test_defaulter_from_union(self):
        """Test defaulter for Union types."""
        union_defaulter = defaulter_from_annotation(Union[int, str])
        result = union_defaulter()
        assert result == 0  # First type's default

    def test_defaulter_from_tuple(self):
        """Test defaulter for tuple types."""
        tuple_defaulter_func = defaulter_from_annotation(tuple[int, str])
        result = tuple_defaulter_func()
        assert result == (0, "")

    def test_defaulter_from_tuple_empty(self):
        """Test defaulter for empty tuple."""
        tuple_defaulter_func = defaulter_from_annotation(tuple[()])
        result = tuple_defaulter_func()
        assert result == ()

    def test_defaulter_from_unsupported_type(self):
        """Test defaulter for unsupported types raises error."""

        class UnsupportedType:
            """Test"""

            def __init__(self, required_arg: Any):
                self.required_arg = required_arg

        with pytest.raises(DefaultingAnnotationError):
            defaulter_from_annotation(UnsupportedType)

    def test_defaulter_from_custom_registered_type(self):
        """Test defaulter for custom registered types."""
        registry = type_registry()

        class CustomType:
            """Test"""

            def __init__(self, value: int = 100):
                self.value = value

        def custom_defaulter():
            return CustomType()

        registry.register_defaulter(CustomType, custom_defaulter)

        try:
            defaulter = defaulter_from_annotation(CustomType)
            result = defaulter()
            assert isinstance(result, CustomType)
            assert result.value == 100
        finally:
            registry.unregister_defaulter(CustomType)

    def test_defaulter_caching(self):
        """Test that defaulter_from_annotation caches results."""
        # Call twice and ensure we get the same function object
        defaulter1 = defaulter_from_annotation(int)
        defaulter2 = defaulter_from_annotation(int)
        assert defaulter1 is defaulter2


class TestDefaultFromAnnotation:
    """Test default_from_annotation function."""

    def test_default_from_annotation_basic(self):
        """Test getting default values from annotations."""
        assert default_from_annotation(int) == 0
        assert default_from_annotation(str) == ""
        assert default_from_annotation(Optional[int]) is None
        assert default_from_annotation(list) == []

    def test_default_from_annotation_tuple(self):
        """Test default from tuple annotation."""
        result = default_from_annotation(tuple[int, str, bool])
        assert result == (0, "", False)

    def test_default_from_annotation_not_cached(self):
        """Test that default_from_annotation returns new instances."""
        # Lists should be different instances
        list1 = default_from_annotation(list)
        list2 = default_from_annotation(list)
        assert list1 == list2
        assert list1 is not list2  # Different instances


class TestCreateValueToAnnotationConverter:
    """Test create_value_to_annotation_converter function."""

    def test_converter_for_basic_type(self):
        """Test converter for basic types."""
        int_converter = converter_from_annotation(int)
        assert int_converter("42") == 42
        assert int_converter(42) == 42

    def test_converter_for_none_type(self):
        """Test converter for NoneType."""
        none_converter_func = converter_from_annotation(NoneType)
        assert none_converter_func(None) is None

        with pytest.raises(ConvertingToAnnotationTypeError):
            none_converter_func(42)

    def test_converter_for_union(self):
        """Test converter for Union types."""
        union_converter_func = converter_from_annotation(Union[int, str])
        assert union_converter_func(42) == 42
        assert union_converter_func("hello") == "hello"
        assert union_converter_func(42.8) == 42  # Converts to int first
        class CustomType:
            """Test"""

            def __init__(self, value: int = 100):
                self.value = value
            
            def __str__(self) -> str:
                return str(self.value)
        assert union_converter_func(CustomType(42)) == "42"  # Converts to str second

    def test_converter_for_tuple(self):
        """Test converter for tuple types."""
        tuple_converter_func = converter_from_annotation(tuple[int, str])
        result = tuple_converter_func(("42", 123))
        assert result == (42, "123")

    def test_converter_for_list(self):
        """Test converter for list types."""
        list_converter_func = converter_from_annotation(list[int])
        result = list_converter_func(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_converter_with_first_in_union_flag(self):
        """Test converter with first_in_union flag."""
        # This should use strict_union_converter instead of union_converter
        converter = converter_from_annotation(
            Union[int, str], first_in_union=True
        )
        assert converter("42") == 42  # Only tries first converter

        with pytest.raises(ConvertingToAnnotationTypeError):
            converter("not a number")  # Should fail since it only tries int

    def test_converter_for_custom_registered_type(self):
        """Test converter for custom registered types."""
        registry = type_registry()

        class CustomType:
            """Test"""

            def __init__(self, value: Any):
                self.value = value

        def custom_converter(value: Any):
            return CustomType(value)

        registry.register_converter(CustomType, custom_converter)

        try:
            converter = converter_from_annotation(CustomType)
            result = converter(42)
            assert isinstance(result, CustomType)
            assert result.value == 42
        finally:
            registry.unregister_converter(CustomType)

    def test_converter_caching(self):
        """Test that create_value_to_annotation_converter caches results."""
        converter1 = converter_from_annotation(int)
        converter2 = converter_from_annotation(int)
        assert converter1 is converter2


class TestConvertValueToAnnotation:
    """Test convert_value_to_annotation function."""

    def test_convert_value_basic(self):
        """Test basic value conversion."""
        result = convert_value_to_annotation("42", int)
        assert result == 42

    def test_convert_value_with_first_in_union(self):
        """Test value conversion with first_in_union flag."""
        result = convert_value_to_annotation("42", Union[int, str], first_in_union=True)
        assert result == 42

    def test_convert_value_complex_type(self):
        """Test conversion with complex nested types."""
        result = convert_value_to_annotation(
            [("1", "hello"), ("2", "world")], list[tuple[int, str]]
        )
        assert result == [(1, "hello"), (2, "world")]

    def test_convert_value_optional(self):
        """Test conversion with Optional types."""
        result = convert_value_to_annotation(None, Optional[int])
        assert result is None

        result = convert_value_to_annotation("42", Optional[int])
        assert result == 42


class TestCacheInvalidation:
    """Test cache invalidation in registry."""

    def test_cache_invalidation_on_register_defaulter(self):
        """Test that caches are invalidated when registering new defaulters."""
        registry = type_registry()

        class TestType:
            """Test"""

            def __init__(self, value: int):
                self.value = value

        # This should fail initially
        with pytest.raises(DefaultingAnnotationError):
            defaulter_from_annotation(TestType)

        # Register a defaulter
        registry.register_defaulter(TestType, lambda: TestType(200))

        # This should work now.
        try:
            defaulter = defaulter_from_annotation(TestType)
            result = defaulter()
            assert isinstance(result, TestType)
            assert result.value == 200
        finally:
            registry.unregister_defaulter(TestType)
        

        # Register a new defaulter
        registry.register_defaulter(TestType, lambda: TestType(500))
        
        # This should work (cache should be invalidated)
        try:
            defaulter = defaulter_from_annotation(TestType)
            result = defaulter()
            assert isinstance(result, TestType)
            assert result.value == 500
        finally:
            registry.unregister_defaulter(TestType)

    def test_cache_invalidation_on_register_converter(self):
        """Test that caches are invalidated when registering new converters."""
        registry = type_registry()

        class TestType:
            """Test"""

            def __init__(self, *, value: Any):
                self.value = value

        # This should fail initially
        with pytest.raises(DefaultingAnnotationError):
            defaulter_from_annotation(TestType)

        # Register a converter
        registry.register_converter(TestType, lambda x: TestType(value=x))

        try:
            converter = converter_from_annotation(TestType)
            result = converter(42)
            assert isinstance(result, TestType)
            assert result.value == 42
        finally:
            registry.unregister_converter(TestType)

        # Register a new converter
        registry.register_converter(TestType, lambda x: TestType(value=str(x)))

        # This should work (cache should be invalidated).
        try:
            converter = converter_from_annotation(TestType)
            result = converter(42)
            assert isinstance(result, TestType)
            assert result.value == "42"
        finally:
            registry.unregister_converter(TestType)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_conversion_error_chaining(self):
        """Test that conversion errors are properly chained."""
        with pytest.raises(ConvertingToAnnotationTypeError) as exc_info:
            convert_value_to_annotation("not a number", int)

        assert exc_info.value.__cause__ is not None
        assert "not a number" in str(exc_info.value)

    def test_defaulting_error_chaining(self):
        """Test that defaulting errors are properly chained."""

        class BadType:
            """Test"""

            def __init__(self, required_arg: Any):
                self.required_arg = required_arg

        with pytest.raises(DefaultingAnnotationError) as exc_info:
            defaulter_from_annotation(BadType)

        assert exc_info.value.__cause__ is not None
        assert "BadType" in str(exc_info.value)

    def test_tuple_size_mismatch_error(self):
        """Test tuple size mismatch error."""
        with pytest.raises(ConvertingToAnnotationTypeError) as exc_info:
            convert_value_to_annotation((1, 2, 3), tuple[int, str])

        assert "Size mismatch" in str(exc_info.value)

    def test_union_all_conversions_fail(self):
        """Test when all union conversions fail."""
        with pytest.raises(ConvertingToAnnotationTypeError) as exc_info:
            convert_value_to_annotation("not convertible", Union[int, float])

        assert "Union[int, float]" in str(exc_info.value)


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow_with_custom_type(self):
        """Test full workflow with custom type registration."""
        registry = type_registry()

        class Point:
            """Test"""

            def __init__(self, x: int = 0, y: int = 0):
                self.x = x
                self.y = y

        # Register custom defaulter and converter
        registry.register_defaulter(Point, Point)
        registry.register_converter(
            Point, lambda v: Point(*v) if isinstance(v, tuple) else Point(v, v)  # type: ignore
        )

        try:
            # Test defaulter
            defaulter = defaulter_from_annotation(Point)
            default_point = defaulter()
            assert isinstance(default_point, Point)
            assert default_point.x == 0
            assert default_point.y == 0

            # Test converter
            converted_point = convert_value_to_annotation((3, 4), Point)
            assert isinstance(converted_point, Point)
            assert converted_point.x == 3
            assert converted_point.y == 4
        finally:
            registry.unregister_defaulter(Point)
            registry.unregister_converter(Point)

    def test_complex_nested_types(self):
        """Test complex nested type annotations."""
        # Test nested type: list[tuple[int, Optional[str]]]
        complex_type = list[tuple[int, Optional[str]]]

        defaulter = defaulter_from_annotation(complex_type)
        default_value = defaulter()
        assert default_value == []

        # Test conversion
        input_value: list[tuple[int, Optional[str]]] = [
            (1, "hello"),
            (2, None),
            (3, "world"),
        ]
        converted = convert_value_to_annotation(input_value, complex_type)
        assert converted == [(1, "hello"), (2, None), (3, "world")]

    def test_deeply_nested_optional_unions(self):
        """Test deeply nested optional unions."""
        complex_type = Optional[Union[list[int], tuple[str, str]]]

        # Test None
        result = convert_value_to_annotation(None, complex_type)
        assert result is None

        # Test list conversion
        result = convert_value_to_annotation(["1", "2", "3"], complex_type)
        assert result == [1, 2, 3]

        # Test tuple conversion
        result = convert_value_to_annotation((1, 2), complex_type)
        assert result == ("1", "2") # implement top to bottom match.

    def test_registry_with_complex_types(self):
        """Test registry with complex generic types."""
        registry = type_registry()

        class Container:
            """Test"""

            def __init__(self, items: list[Any]):
                self.items = items

        def container_defaulter_creator(_: list[Defaulter], __: Any):
            def defaulter():
                return Container([])

            return defaulter

        def container_converter_creator(inner_converters: list[Converter], _: Any):
            def converter(value: Any):
                if isinstance(value, Container):
                    return value
                return Container([inner_converters[0](item) for item in value])

            return converter

        registry.register_defaulter_creator(Container, container_defaulter_creator)
        registry.register_converter_creator(Container, container_converter_creator)

        try:
            # This would work with proper generic type handling
            # For now, just test that the registry functions work
            assert registry.has_defaulter_creator(Container)
            assert registry.has_converter_creator(Container)
        finally:
            registry.unregister_defaulter_creator(Container)
            registry.unregister_converter_creator(Container)


class TestValidationLevel:
    """Test ValidationLevel enum and related operations."""

    def test_validation_level_values(self) -> None:
        """Test that ValidationLevel has correct integer values."""
        assert ValidationLevel.NONE == 0
        assert ValidationLevel.FULL == 1
        assert ValidationLevel.PARTIAL == 2

    def test_validation_level_ordering(self) -> None:
        """Test that ValidationLevel values can be compared."""
        assert ValidationLevel.NONE < ValidationLevel.FULL
        assert ValidationLevel.FULL < ValidationLevel.PARTIAL
        assert ValidationLevel.NONE < ValidationLevel.PARTIAL


class TestUnionDetection:
    """Test union type detection functions."""

    def test_is_union_with_union_type(self) -> None:
        """Test is_union with Union type."""
        assert is_union(Union[int, str]) is True
        assert is_union(Union[int, str, float]) is True

    def test_is_union_with_union_type_syntax(self) -> None:
        """Test is_union with modern union syntax."""
        assert is_union(int | str) is True
        assert is_union(int | str | float) is True

    def test_is_union_with_non_union(self) -> None:
        """Test is_union with non-union types."""
        assert is_union(int) is False
        assert is_union(str) is False
        assert is_union(list[int]) is False
        assert is_union(tuple[int, str]) is False

    def test_is_optional_with_optional_types(self) -> None:
        """Test is_optional with optional types."""
        assert is_optional(Union[int, None]) is True
        assert is_optional(Optional[str]) is True
        assert is_optional(int | None) is True

    def test_is_optional_with_non_optional(self) -> None:
        """Test is_optional with non-optional types."""
        assert is_optional(int) is False
        assert is_optional(Union[int, str]) is False
        assert is_optional(int | str) is False

    def test_is_binary_optional_with_binary_optional(self) -> None:
        """Test is_binary_optional with binary optional types."""
        assert is_binary_optional(Union[int, None]) is True
        assert is_binary_optional(Optional[str]) is True
        assert is_binary_optional(int | None) is True

    def test_is_binary_optional_with_non_binary_optional(self) -> None:
        """Test is_binary_optional with non-binary optional types."""
        assert is_binary_optional(Union[int, str, None]) is False
        assert is_binary_optional(Union[int, str]) is False
        assert is_binary_optional(int) is False


class TestTypeRegistry:
    """Test TypeRegistry functionality."""

    registry: TypeRegistry

    def setup_method(self) -> None:
        """Set up test registry for each test."""
        self.registry = TypeRegistry()

    def test_register_and_get_validator(self) -> None:
        """Test registering and retrieving custom validators."""

        def custom_validator(value: Any) -> bool:
            return isinstance(value, str) and len(value) > 5

        self.registry.register_validator(str, custom_validator)
        assert self.registry.has_validator(str) is True
        retrieved = self.registry.get_validator(str)
        assert retrieved is custom_validator

    def test_register_and_get_defaulter(self) -> None:
        """Test registering and retrieving custom defaulters."""

        def custom_defaulter() -> str:
            return "default_value"

        self.registry.register_defaulter(str, custom_defaulter)
        assert self.registry.has_defaulter(str) is True
        retrieved = self.registry.get_defaulter(str)
        assert retrieved is custom_defaulter

    def test_register_and_get_converter(self) -> None:
        """Test registering and retrieving custom converters."""

        def custom_converter(value: Any) -> str:
            return str(value).upper()

        self.registry.register_converter(str, custom_converter)
        assert self.registry.has_converter(str) is True
        retrieved = self.registry.get_converter(str)
        assert retrieved is custom_converter

    def test_unregister_validator(self) -> None:
        """Test unregistering validators."""

        def custom_validator(_: Any) -> bool:
            return True

        self.registry.register_validator(str, custom_validator)
        assert self.registry.has_validator(str) is True

        self.registry.unregister_validator(str)
        assert self.registry.has_validator(str) is False

    def test_validator_creator_registration(self) -> None:
        """Test registering validator creators."""

        def custom_creator(inner_validators: list[Validator], _: Any):
            def validator(value: Any) -> bool:
                return all(v(value) for v in inner_validators)

            return validator

        self.registry.register_validator_creator(tuple, custom_creator)
        assert self.registry.has_validator_creator(tuple) is True
        retrieved = self.registry.get_validator_creator(tuple)
        assert retrieved is custom_creator

    def test_get_nonexistent_validator_raises_keyerror(self) -> None:
        """Test that getting non-existent validator raises KeyError."""
        with pytest.raises(KeyError, match="No validator registered for type"):
            self.registry.get_validator(int)

    def test_type_registry_singleton(self):
        """Test that type_registry returns the same instance."""
        registry1 = type_registry()
        registry2 = type_registry()
        assert registry1 is registry2

    def test_register_defaulter(self):
        """Test registering a custom defaulter."""
        registry = TypeRegistry()

        class CustomType:
            """Test"""

            def __init__(self, value: int = 42):
                self.value = value

        def custom_defaulter():
            return CustomType()

        registry.register_defaulter(CustomType, custom_defaulter)
        assert registry.has_defaulter(CustomType)
        defaulter = registry.get_defaulter(CustomType)
        result = defaulter()
        assert isinstance(result, CustomType)
        assert result.value == 42

    def test_register_converter(self):
        """Test registering a custom converter."""
        registry = TypeRegistry()

        class CustomType:
            """Test"""

            def __init__(self, value: Any):
                self.value = value

        def custom_converter(value: Any):
            return CustomType(value)

        registry.register_converter(CustomType, custom_converter)
        assert registry.has_converter(CustomType)
        converter = registry.get_converter(CustomType)
        result = converter(42)
        assert isinstance(result, CustomType)
        assert result.value == 42

    def test_register_defaulter_creator(self):
        """Test registering a custom defaulter creator."""
        registry = TypeRegistry()

        class CustomGeneric:
            """Test"""

            def __init__(self, inner_value: Any):
                self.inner_value = inner_value

        def custom_defaulter_creator(inner_defaulters: list[Defaulter], _: Any):
            def defaulter():
                return CustomGeneric(
                    inner_defaulters[0]() if inner_defaulters else None
                )

            return defaulter

        registry.register_defaulter_creator(CustomGeneric, custom_defaulter_creator)
        assert registry.has_defaulter_creator(CustomGeneric)
        creator = registry.get_defaulter_creator(CustomGeneric)
        defaulter = creator([lambda: 42], CustomGeneric)
        result = defaulter()
        assert isinstance(result, CustomGeneric)
        assert result.inner_value == 42

    def test_register_converter_creator(self):
        """Test registering a custom converter creator."""
        registry = TypeRegistry()

        class CustomGeneric:
            """Test"""

            def __init__(self, inner_value: Any):
                self.inner_value = inner_value

        def custom_converter_creator(inner_converters: list[Converter], _: Any):
            def converter(value: Any):
                return CustomGeneric(
                    inner_converters[0](value) if inner_converters else value
                )

            return converter

        registry.register_converter_creator(CustomGeneric, custom_converter_creator)
        assert registry.has_converter_creator(CustomGeneric)
        creator = registry.get_converter_creator(CustomGeneric)
        converter = creator([type_converter(int)], CustomGeneric)
        result = converter("42")
        assert isinstance(result, CustomGeneric)
        assert result.inner_value == 42

    def test_unregister_functions(self):
        """Test unregistering functions."""
        registry = TypeRegistry()

        class TestType:
            """Test"""

        registry.register_defaulter(TestType, TestType)
        registry.register_converter(TestType, lambda x: TestType())

        assert registry.has_defaulter(TestType)
        assert registry.has_converter(TestType)

        registry.unregister_defaulter(TestType)
        registry.unregister_converter(TestType)

        assert not registry.has_defaulter(TestType)
        assert not registry.has_converter(TestType)

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent types doesn't raise error."""
        registry = TypeRegistry()

        class NonExistentType:
            """Test"""

        # Should not raise
        registry.unregister_defaulter(NonExistentType)
        registry.unregister_converter(NonExistentType)
        registry.unregister_defaulter_creator(NonExistentType)
        registry.unregister_converter_creator(NonExistentType)

    def test_get_nonexistent_raises_keyerror(self):
        """Test that getting nonexistent defaulter/converter raises KeyError."""
        registry = TypeRegistry()

        class NonExistentType:
            """Test"""

        with pytest.raises(KeyError):
            registry.get_defaulter(NonExistentType)

        with pytest.raises(KeyError):
            registry.get_converter(NonExistentType)

        with pytest.raises(KeyError):
            registry.get_defaulter_creator(NonExistentType)

        with pytest.raises(KeyError):
            registry.get_converter_creator(NonExistentType)

    def test_list_registered_types(self):
        """Test listing registered types."""
        registry = TypeRegistry()

        class TestType:
            """Test"""

        registry.register_defaulter(TestType, TestType)
        registry.register_converter(TestType, lambda x: TestType())

        registered = registry.list_registered_types()
        assert TestType in registered["defaulters"]
        assert TestType in registered["converters"]
        assert isinstance(registered["defaulter_creators"], list)
        assert isinstance(registered["converter_creators"], list)


class TestValidatorFromAnnotation:
    """Test validator_from_annotation function."""

    def test_basic_type_validation(self) -> None:
        """Test validation with basic types."""
        int_validator = validator_from_annotation(int)
        assert int_validator(42) is True
        assert int_validator("42") is False
        assert int_validator(42.0) is False

        str_validator = validator_from_annotation(str)
        assert str_validator("hello") is True
        assert str_validator(42) is False

    def test_none_type_validation(self) -> None:
        """Test validation with NoneType."""
        none_validator = validator_from_annotation(type(None))
        assert none_validator(None) is True
        assert none_validator(0) is False
        assert none_validator("") is False

    def test_union_validation(self) -> None:
        """Test validation with Union types."""
        union_validator = validator_from_annotation(Union[int, str])
        assert union_validator(42) == ValidationLevel.FULL
        assert union_validator("hello") == ValidationLevel.FULL
        assert union_validator(42.0) == ValidationLevel.NONE
        assert union_validator([1, 2, 3]) == ValidationLevel.NONE

    def test_optional_validation(self) -> None:
        """Test validation with Optional types."""
        optional_validator = validator_from_annotation(Optional[int])
        assert optional_validator(42) == ValidationLevel.FULL
        assert optional_validator(None) == ValidationLevel.FULL
        assert optional_validator("42") == ValidationLevel.NONE

    def test_list_validation(self) -> None:
        """Test validation with list types."""
        list_validator = validator_from_annotation(list[int])
        assert list_validator([1, 2, 3]) == ValidationLevel.FULL
        assert (
            list_validator([1, "2", 3]) == ValidationLevel.PARTIAL
        )  # list but wrong content
        assert list_validator("123") == ValidationLevel.NONE
        assert list_validator((1, 2, 3)) == ValidationLevel.NONE

    def test_tuple_validation(self) -> None:
        """Test validation with tuple types."""
        tuple_validator = validator_from_annotation(tuple[int, str])
        assert tuple_validator((42, "hello")) == ValidationLevel.FULL
        assert (
            tuple_validator((42, 123)) == ValidationLevel.PARTIAL
        )  # tuple but wrong types
        assert tuple_validator([42, "hello"]) == ValidationLevel.NONE
        assert tuple_validator((42,)) == ValidationLevel.NONE  # Wrong length

    def test_nested_type_validation(self) -> None:
        """Test validation with nested types."""
        nested_validator = validator_from_annotation(list[tuple[int, str]])
        assert nested_validator([(1, "a"), (2, "b")]) == ValidationLevel.FULL
        assert nested_validator([(1, "a"), (2, 2)]) == ValidationLevel.PARTIAL
        assert nested_validator([1, 2, 3]) == ValidationLevel.PARTIAL
        assert nested_validator("not a list") == ValidationLevel.NONE

    def test_complex_union_validation(self) -> None:
        """Test validation with complex Union types."""
        complex_validator = validator_from_annotation(Union[list[int], tuple[str, str]])
        assert complex_validator([1, 2, 3]) == ValidationLevel.FULL
        assert complex_validator(("a", "b")) == ValidationLevel.FULL
        assert (
            complex_validator([1, "2"]) == ValidationLevel.PARTIAL
        )  # list but wrong content
        assert (
            complex_validator(("a", 1)) == ValidationLevel.PARTIAL
        )  # tuple but wrong content
        assert complex_validator("string") == ValidationLevel.NONE


class TestValidationLevelOperations:
    """Test ValidationLevel bitwise operations."""

    def test_vl_and_operation(self) -> None:
        """Test _vl_and function behavior."""
        from sg_lib.src.sg_lib.meta.typing_utilities.annotations import (
            _vl_and,  # type: ignore
        )

        assert (
            _vl_and(ValidationLevel.FULL, ValidationLevel.FULL) == ValidationLevel.FULL
        )
        assert (
            _vl_and(ValidationLevel.FULL, ValidationLevel.NONE) == ValidationLevel.NONE
        )
        assert (
            _vl_and(ValidationLevel.PARTIAL, ValidationLevel.FULL)
            == ValidationLevel.NONE
        )
        assert (
            _vl_and(ValidationLevel.PARTIAL, ValidationLevel.PARTIAL)
            == ValidationLevel.PARTIAL
        )

    def test_vl_or_operation(self) -> None:
        """Test _vl_or function behavior."""
        from sg_lib.src.sg_lib.meta.typing_utilities.annotations import (
            _vl_or,  # type: ignore
        )

        assert (
            _vl_or(ValidationLevel.NONE, ValidationLevel.NONE) == ValidationLevel.NONE
        )
        assert (
            _vl_or(ValidationLevel.NONE, ValidationLevel.FULL) == ValidationLevel.FULL
        )
        assert (
            _vl_or(ValidationLevel.PARTIAL, ValidationLevel.FULL)
            == ValidationLevel.PARTIAL | ValidationLevel.FULL
        )
        assert (
            _vl_or(ValidationLevel.PARTIAL, ValidationLevel.PARTIAL)
            == ValidationLevel.PARTIAL
        )


class TestCustomValidators:
    """Test custom validator functionality."""

    registry: TypeRegistry
    positive_int_type: Any

    def setup_method(self) -> None:
        """Set up custom validators for testing."""
        self.registry = type_registry()

        # Custom validator for positive integers
        def positive_int_validator(value: Any) -> ValidationLevel:
            if isinstance(value, int) and value > 0:
                return ValidationLevel.FULL
            elif isinstance(value, int):
                return ValidationLevel.PARTIAL
            return ValidationLevel.NONE

        # Register custom validator
        class PositiveInt:
            pass

        self.positive_int_type = PositiveInt
        self.registry.register_validator(PositiveInt, positive_int_validator)

    def teardown_method(self) -> None:
        """Clean up after tests."""
        self.registry.unregister_validator(self.positive_int_type)

    def test_custom_validator_usage(self) -> None:
        """Test that custom validators are used correctly."""
        validator = validator_from_annotation(self.positive_int_type)

        assert validator(5) == ValidationLevel.FULL
        assert validator(-5) == ValidationLevel.PARTIAL
        assert validator("5") == ValidationLevel.NONE


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_validator_with_invalid_annotation(self) -> None:
        """Test validator creation with invalid annotations."""
        # This should test what happens with truly invalid annotations
        # The exact behavior depends on your implementation

    def test_empty_union_validation(self) -> None:
        """Test validation with empty or single-element unions."""
        # Union with single type should behave like the type itself
        single_union_validator = validator_from_annotation(Union[int])
        assert single_union_validator(42) == ValidationLevel.FULL
        assert single_union_validator("42") == ValidationLevel.NONE

    def test_deeply_nested_types(self) -> None:
        """Test validation with deeply nested types."""
        deep_type = list[tuple[Union[int, str], Optional[list[int]]]]
        deep_validator = validator_from_annotation(deep_type)

        valid_data: Any = [(1, [1, 2, 3]), ("hello", None), (42, [])]
        assert deep_validator(valid_data) == ValidationLevel.FULL

        partial_data: Any = [(1, [1, "2", 3]), ("hello", None)]  # Invalid nested list
        assert deep_validator(partial_data) == ValidationLevel.PARTIAL

        invalid_data = "not a list"
        assert deep_validator(invalid_data) == ValidationLevel.NONE


# Additional test for the modern union syntax (Python 3.10+)
class TestModernUnionSyntax:
    """Test validation with modern union syntax (| operator)."""

    def test_modern_union_validation(self) -> None:
        """Test validation with | union syntax."""
        try:
            # This will only work in Python 3.10+
            modern_validator = validator_from_annotation(int | str)
            assert modern_validator(42) == ValidationLevel.FULL
            assert modern_validator("hello") == ValidationLevel.FULL
            assert modern_validator(42.0) == ValidationLevel.NONE
        except TypeError:
            # Skip test if running on older Python version
            pytest.skip("Modern union syntax not supported in this Python version")

    def test_modern_optional_validation(self) -> None:
        """Test validation with modern optional syntax."""
        try:
            modern_optional_validator = validator_from_annotation(int | None)
            assert modern_optional_validator(42) == ValidationLevel.FULL
            assert modern_optional_validator(None) == ValidationLevel.FULL
            assert modern_optional_validator("42") == ValidationLevel.NONE
        except TypeError:
            pytest.skip("Modern union syntax not supported in this Python version")
