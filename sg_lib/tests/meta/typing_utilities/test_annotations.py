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
Description: Tests for the annotations processors module.
🦙

Note: Updated to test the new annotation registry architecture.
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from typing import Union, Optional, Any, Literal, Final, ClassVar
from types import NoneType

import pytest

from sg_lib.src.sg_lib.meta.typing_utilities.annotations_processors.errors import (
    TypingError,
    DefaultingAnnotationError,
    ConvertingToAnnotationTypeError,
)
from sg_lib.src.sg_lib.meta.typing_utilities.annotations_processors.processors import (
    AnnotationsRegistery,
    AnnotationEntry,
    ValidationLevel,
    annotation_registry,
    validator_from_annotation,
    defaulter_from_annotation,
    default_from_annotation,
    convert_to_annotation,
    vl_and,
    vl_or,
)
from sg_lib.src.sg_lib.meta.typing_utilities.utilities import (
    is_union,
    is_optional,
    is_binary_optional,
    resolve_annotation_types,
)


class TestExceptions:
    """Test custom exception classes."""

    def test_typing_error_inheritance(self):
        """Test that TypingError inherits from Exception."""
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


class TestValidationLevel:
    """Test ValidationLevel enum and bitwise operations."""

    def test_validation_level_values(self):
        """Test that ValidationLevel has correct integer values."""
        assert ValidationLevel.NONE == 0
        assert ValidationLevel.FULL == 1
        assert ValidationLevel.PARTIAL == 2

    def test_validation_level_ordering(self):
        """Test that ValidationLevel values can be compared."""
        assert ValidationLevel.NONE < ValidationLevel.FULL
        assert ValidationLevel.FULL < ValidationLevel.PARTIAL

    def test_vl_and_operation(self):
        """Test vl_and function behavior."""
        assert (
            vl_and(ValidationLevel.FULL, ValidationLevel.FULL) == ValidationLevel.FULL
        )
        assert (
            vl_and(ValidationLevel.FULL, ValidationLevel.NONE) == ValidationLevel.NONE
        )
        assert (
            vl_and(ValidationLevel.PARTIAL, ValidationLevel.FULL)
            == ValidationLevel.NONE
        )
        assert (
            vl_and(ValidationLevel.PARTIAL, ValidationLevel.PARTIAL)
            == ValidationLevel.PARTIAL
        )

    def test_vl_or_operation(self):
        """Test vl_or function behavior."""
        assert vl_or(ValidationLevel.NONE, ValidationLevel.NONE) == ValidationLevel.NONE
        assert vl_or(ValidationLevel.NONE, ValidationLevel.FULL) == ValidationLevel.FULL
        assert vl_or(ValidationLevel.PARTIAL, ValidationLevel.FULL) == (
            ValidationLevel.PARTIAL | ValidationLevel.FULL
        )
        assert (
            vl_or(ValidationLevel.PARTIAL, ValidationLevel.PARTIAL)
            == ValidationLevel.PARTIAL
        )


class TestTypeUtilities:
    """Test type checking utility functions."""

    def test_is_union_with_union_type(self):
        """Test is_union with Union type."""
        assert is_union(Union[int, str]) is True
        assert is_union(int) is False
        assert is_union(Optional[int]) is True  # Optional is Union[T, None]

    def test_is_union_with_modern_syntax(self):
        """Test is_union with modern union syntax (Python 3.10+)."""
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


class TestBasicConversion:
    """Test basic type conversion functionality."""

    def test_convert_basic_types(self):
        """Test conversion of basic types."""
        assert convert_to_annotation(int, "42") == 42
        assert convert_to_annotation(str, 42) == "42"
        assert convert_to_annotation(float, "3.14") == 3.14
        assert convert_to_annotation(bool, 1) is True

    def test_convert_none_type(self):
        """Test conversion to NoneType."""
        assert convert_to_annotation(NoneType, None) is None
        with pytest.raises(ConvertingToAnnotationTypeError):
            convert_to_annotation(NoneType, 42)

    def test_convert_optional_types(self):
        """Test conversion with Optional types."""
        assert convert_to_annotation(Optional[int], None) is None
        assert convert_to_annotation(Optional[int], "42") == 42
        assert convert_to_annotation(Optional[str], None) is None


class TestListConversion:
    """Test list type conversion."""

    def test_convert_list_of_ints(self):
        """Test converting list with int elements."""
        result = convert_to_annotation(list[int], ["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_convert_list_of_strings(self):
        """Test converting list with string elements."""
        result = convert_to_annotation(list[str], [1, 2, 3])
        assert result == ["1", "2", "3"]

    def test_convert_empty_list(self):
        """Test converting empty list."""
        result = convert_to_annotation(list[int], [])
        assert result == []

    def test_convert_nested_lists(self):
        """Test converting nested lists."""
        result = convert_to_annotation(list[list[int]], [["1", "2"], ["3", "4"]])
        assert result == [[1, 2], [3, 4]]


class TestTupleConversion:
    """Test tuple type conversion."""

    def test_convert_tuple_basic(self):
        """Test basic tuple conversion."""
        result = convert_to_annotation(tuple[int, str], ("42", 123))
        assert result == (42, "123")

    def test_convert_tuple_mixed_types(self):
        """Test tuple with mixed types."""
        result = convert_to_annotation(tuple[int, str, float], ("1", 2, "3.14"))
        assert result == (1, "2", 3.14)

    def test_convert_tuple_size_mismatch(self):
        """Test that tuple size mismatch raises error."""
        with pytest.raises(ConvertingToAnnotationTypeError):
            convert_to_annotation(tuple[int, str], (1,))


class TestDictConversion:
    """Test dict type conversion."""

    def test_convert_dict_basic(self):
        """Test basic dict conversion."""
        result = convert_to_annotation(dict[str, int], {1: "2", 3: "4"})
        assert result == {"1": 2, "3": 4}

    def test_convert_dict_complex(self):
        """Test dict with complex value types."""
        result = convert_to_annotation(
            dict[str, list[int]], {"a": ["1", "2"], "b": ["3"]}
        )
        assert result == {"a": [1, 2], "b": [3]}

    def test_convert_empty_dict(self):
        """Test converting empty dict."""
        result = convert_to_annotation(dict[str, int], {})
        assert result == {}


class TestSetConversion:
    """Test set type conversion."""

    def test_convert_set_basic(self):
        """Test basic set conversion."""
        result = convert_to_annotation(set[int], {"1", "2", "3"})
        assert result == {1, 2, 3}

    def test_convert_set_from_list(self):
        """Test converting list to set."""
        result = convert_to_annotation(set[int], ["1", "2", "3"])
        assert result == {1, 2, 3}

    def test_convert_empty_set(self):
        """Test converting empty set."""
        result = convert_to_annotation(set[int], set())
        assert result == set()


class TestLiteralConversion:
    """Test Literal type conversion."""

    def test_convert_literal_match(self):
        """Test conversion with matching literal value."""
        result = convert_to_annotation(Literal["a", "b", "c"], "a")
        assert result == "a"

    def test_convert_literal_no_match(self):
        """Test conversion with non-matching value uses first literal."""
        result = convert_to_annotation(Literal["a", "b", "c"], "d")
        assert result == "a"

    def test_convert_literal_int(self):
        """Test Literal with int values."""
        result = convert_to_annotation(Literal[1, 2, 3], 2)
        assert result == 2


class TestFinalAndClassVarConversion:
    """Test Final and ClassVar type conversion."""

    def test_convert_final_int(self):
        """Test conversion with Final wrapper."""
        result = convert_to_annotation(Final[int], "42")
        assert result == 42

    def test_convert_classvar_int(self):
        """Test conversion with ClassVar wrapper."""
        result = convert_to_annotation(ClassVar[int], "42")
        assert result == 42

    def test_convert_final_list(self):
        """Test Final with complex type."""
        result = convert_to_annotation(Final[list[int]], ["1", "2"])
        assert result == [1, 2]


class TestUnionConversion:
    """Test Union type conversion."""

    def test_convert_union_first_match(self):
        """Test union conversion with first type matching."""
        result = convert_to_annotation(Union[int, str], 42)
        assert result == 42

    def test_convert_union_second_match(self):
        """Test union conversion with second type matching."""
        result = convert_to_annotation(Union[int, str], "hello")
        assert result == "hello"

    def test_convert_union_conversion_needed(self):
        """Test union conversion requiring type conversion."""
        result = convert_to_annotation(Union[int, str], 42.8)
        assert result == 42  # Should convert to int (first type)


class TestComplexNestedTypes:
    """Test complex nested type conversions."""

    def test_nested_list_tuple(self):
        """Test list of tuples."""
        result = convert_to_annotation(list[tuple[int, str]], [("1", 2), ("3", 4)])
        assert result == [(1, "2"), (3, "4")]

    def test_dict_with_list_values(self):
        """Test dict with list values."""
        result = convert_to_annotation(dict[str, list[int]], {1: ["1", "2"], 2: ["3"]})
        assert result == {"1": [1, 2], "2": [3]}

    def test_optional_list(self):
        """Test Optional list."""
        assert convert_to_annotation(Optional[list[int]], None) is None
        assert convert_to_annotation(Optional[list[int]], ["1", "2"]) == [1, 2]


class TestDefaultValues:
    """Test default value generation."""

    def test_default_basic_types(self):
        """Test defaults for basic types."""
        assert default_from_annotation(int) == 0
        assert default_from_annotation(str) == ""
        assert default_from_annotation(float) == 0.0
        assert default_from_annotation(bool) is False

    def test_default_collections(self):
        """Test defaults for collection types."""
        assert default_from_annotation(list) == []
        assert default_from_annotation(dict) == {}
        assert default_from_annotation(set) == set()

    def test_default_tuple(self):
        """Test default for tuple type."""
        result = default_from_annotation(tuple[int, str])
        assert result == (0, "")

    def test_default_optional(self):
        """Test default for Optional type."""
        assert default_from_annotation(Optional[int]) is None

    def test_default_none_type(self):
        """Test default for NoneType."""
        defaulter = defaulter_from_annotation(NoneType)
        assert defaulter() is None


class TestValidation:
    """Test type validation functionality."""

    def test_validate_basic_types(self):
        """Test validation with basic types."""
        int_validator = validator_from_annotation(int)
        assert int_validator(42) is True
        assert int_validator("42") is False

    def test_validate_list(self):
        """Test list validation."""
        list_validator = validator_from_annotation(list[int])
        assert list_validator([1, 2, 3]) == ValidationLevel.FULL
        assert list_validator([1, "2", 3]) == ValidationLevel.PARTIAL
        assert list_validator("not a list") == ValidationLevel.NONE

    def test_validate_tuple(self):
        """Test tuple validation."""
        tuple_validator = validator_from_annotation(tuple[int, str])
        assert tuple_validator((42, "hello")) == ValidationLevel.FULL
        assert tuple_validator((42, 123)) == ValidationLevel.PARTIAL
        assert tuple_validator([42, "hello"]) == ValidationLevel.NONE

    def test_validate_optional(self):
        """Test Optional validation."""
        optional_validator = validator_from_annotation(Optional[int])
        assert optional_validator(42) == ValidationLevel.FULL
        x = optional_validator(None)
        assert x == ValidationLevel.FULL
        assert optional_validator("42") == ValidationLevel.NONE

    def test_validate_union(self):
        """Test Union validation."""
        union_validator = validator_from_annotation(Union[int, str])
        assert union_validator(42) == ValidationLevel.FULL
        assert union_validator("hello") == ValidationLevel.FULL
        assert union_validator(42.0) == ValidationLevel.NONE


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_conversion_error(self):
        """Test that conversion errors are raised correctly."""
        with pytest.raises(ConvertingToAnnotationTypeError):
            convert_to_annotation(int, "not a number")

    def test_defaulting_error(self):
        """Test that defaulting errors are raised for unsupported types."""

        class UnsupportedType:
            def __init__(self, required_arg: Any):
                self.required_arg = required_arg

        with pytest.raises(DefaultingAnnotationError):
            defaulter_from_annotation(UnsupportedType)


class TestRegistrySingleton:
    """Test annotation registry singleton behavior."""

    def test_registry_singleton(self):
        """Test that annotation_registry returns the same instance."""
        registry1 = annotation_registry()
        registry2 = annotation_registry()
        assert registry1 is registry2

    def test_registry_is_annotations_registery(self):
        """Test that registry is correct type."""
        registry = annotation_registry()
        assert isinstance(registry, AnnotationsRegistery)


class TestCustomTypeRegistration:
    """Test custom type registration functionality."""

    def test_register_custom_validator(self):
        """Test registering a custom validator."""
        registry = annotation_registry()

        class CustomType:
            def __init__(self, value: int = 42):
                self.value = value

        def custom_validator(v: Any) -> bool:
            return isinstance(v, CustomType)

        # Register and use
        registry.register_validator(CustomType, custom_validator)
        validator = validator_from_annotation(CustomType)

        assert validator(CustomType(10)) is True
        assert validator("not custom") is False

    def test_register_custom_defaulter(self):
        """Test registering a custom defaulter."""
        registry = annotation_registry()

        class CustomType:
            def __init__(self, value: int = 42):
                self.value = value

        def custom_defaulter():
            return CustomType(100)

        # Register and use
        registry.register_defaulter(CustomType, custom_defaulter)
        defaulter = defaulter_from_annotation(CustomType)
        result = defaulter()

        assert isinstance(result, CustomType)
        assert result.value == 100

    def test_register_custom_converter(self):
        """Test registering a custom converter."""
        registry = annotation_registry()

        class CustomType:
            def __init__(self, value: Any):
                self.value = value

        def custom_converter(value: Any):
            return CustomType(value)

        # Register and use
        registry.register_converter(CustomType, custom_converter)
        result = convert_to_annotation(CustomType, 42)

        assert isinstance(result, CustomType)
        assert result.value == 42


class TestAnnotationEntry:
    """Test AnnotationEntry base class behavior."""

    def test_annotation_entry_is_abstract(self):
        """Test that AnnotationEntry defines the processor interface."""
        # AnnotationEntry should have the required methods
        assert hasattr(AnnotationEntry, "prepare_inner")
        assert hasattr(AnnotationEntry, "create_validator")
        assert hasattr(AnnotationEntry, "create_defaulter")
        assert hasattr(AnnotationEntry, "create_converter")


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_deeply_nested_conversion(self):
        """Test deeply nested type conversion."""
        complex_type = dict[str, list[tuple[int, Optional[str]]]]
        input_data = {1: [("1", "hello"), ("2", None)], 2: [("3", "world")]}
        result = convert_to_annotation(complex_type, input_data)

        assert result == {"1": [(1, "hello"), (2, None)], "2": [(3, "world")]}
