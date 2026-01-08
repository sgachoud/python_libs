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
Created: 2025-07-11
Updated: 2025-12-15
Description: Comprehensive tests for the ConstantNamespace class and constants module.
🦙

Note: written with the assistance of ChatGPT from OpenAI and Claude AI.
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from pathlib import Path
from typing import Any, Final, ClassVar, Optional

import pytest

from metacore.src.metacore.constants import (
    ConstantNamespace,
    ConstantsCompositionError,
    ConstantsInstantiationError,
    ConstantsModificationError,
)

from metacore.src.metacore.meta.classes.constants import (
    _instantiation_error, # type: ignore
    _verify_functions, # type: ignore
)


# =============================================================================
# Basic Creation and Access Tests
# =============================================================================


class TestConstantNamespaceCreation:
    """Test basic creation and access of constant namespaces."""

    def test_basic_constant_creation(self):
        """Test creating a simple constant namespace."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1
            B: str = "hello"
            C: float = 3.14

        assert TestConstants.A == 1
        assert TestConstants.B == "hello"
        assert TestConstants.C == 3.14

    def test_empty_constant_namespace(self):
        """Test empty constant namespace."""

        class EmptyConstants(ConstantNamespace):
            """Test"""

        assert len(EmptyConstants.__constants__) == 0
        assert not list(EmptyConstants)
        assert EmptyConstants.items() == []

    def test_unannotated_attributes_not_constants(self):
        """Test that unannotated attributes are not considered constants."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A = 1  # Not a constant (no annotation)
            B: int = 2  # This is a constant

        assert "A" not in TestConstants.__constants__
        assert "B" in TestConstants.__constants__
        assert TestConstants.__constants__ == ("B",)


# =============================================================================
# Type Coercion Tests
# =============================================================================


class TestTypeCoercion:
    """Test automatic type coercion of constant values."""

    def test_basic_type_coercion(self):
        """Test that values are coerced to their annotated types."""

        class TestConstants(ConstantNamespace):
            """Test"""

            int_value: int = 3.14  # Should be coerced to 3 # type: ignore
            str_value: str = 123  # Should be coerced to "123" # type: ignore
            float_value: float = 5  # Should be coerced to 5.0

        assert TestConstants.int_value == 3
        assert isinstance(TestConstants.int_value, int)
        assert TestConstants.str_value == "123"
        assert isinstance(TestConstants.str_value, str)
        assert TestConstants.float_value == 5.0
        assert isinstance(TestConstants.float_value, float)

    def test_union_type_coercion(self):
        """Test type coercion with union types."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int | str = "1"  # Preserved as str (already matches union)
            B: int = 1.5  # Coerced to int # type: ignore
            C: int | float | str = 1  # Preserved as int (already matches)

        assert TestConstants.A == "1"
        assert TestConstants.B == 1
        assert TestConstants.C == 1

    def test_union_type_preserves_exact_match(self):
        """Test that union types preserve values that already match one of the union types."""

        class TestConstants(ConstantNamespace):
            """Test"""

            # When value already matches a union type, it's preserved
            int_or_float: int | float = 3.14  # Preserved as float
            str_or_int: str | int = 123  # Preserved as int
            # When value needs conversion, it converts
            float_value: float = 5  # Converts to 5.0

        assert TestConstants.int_or_float == 3.14
        assert isinstance(TestConstants.int_or_float, float)
        assert TestConstants.str_or_int == 123
        assert isinstance(TestConstants.str_or_int, int)
        assert TestConstants.float_value == 5.0
        assert isinstance(TestConstants.float_value, float)

    def test_path_coercion(self):
        """Test coercion to pathlib.Path."""

        class TestConstants(ConstantNamespace):
            """Test"""

            D: Path = "documents/test.txt"  # type: ignore

        assert TestConstants.D == Path("documents/test.txt")
        assert isinstance(TestConstants.D, Path)

    def test_list_coercion(self):
        """Test coercion to typed lists."""

        class TestConstants(ConstantNamespace):
            """Test"""

            int_list: list[int] = [1, 1.5, 3]  # type: ignore

        assert TestConstants.int_list == [1, 1, 3]
        assert all(isinstance(x, int) for x in TestConstants.int_list)

    def test_final_and_classvar_coercion(self):
        """Test coercion with Final and ClassVar wrappers."""

        class TestConstants(ConstantNamespace):
            """Test"""

            E: Final[int] = 1.5  # type: ignore
            F: ClassVar[int] = 1.5  # type: ignore

        assert TestConstants.E == 1
        assert TestConstants.F == 1

    def test_type_coercion_failure(self):
        """Test handling of type coercion failures."""
        with pytest.raises(ConstantsCompositionError) as exc_info:

            class TestConstants(ConstantNamespace):
                """Test"""

                A: int = "not_convertible_to_int"  # type: ignore

            _ = TestConstants.A

        assert "Failed to coerce value" in str(exc_info.value)
        assert "to type" in str(exc_info.value)


# =============================================================================
# Complex Type Coercion Tests
# =============================================================================


class TestComplexTypeCoercion:
    """Test coercion of complex nested types in constants."""

    def test_dict_coercion(self):
        """Test dict type coercion."""

        class TestConstants(ConstantNamespace):
            """Test"""

            simple_dict: dict[str, int] = {1: "2", 3: "4"}  # type: ignore

        assert TestConstants.simple_dict == {"1": 2, "3": 4}

    def test_tuple_coercion(self):
        """Test tuple type coercion."""

        class TestConstants(ConstantNamespace):
            """Test"""

            simple_tuple: tuple[int, str] = (42, 123)  # type: ignore

        assert TestConstants.simple_tuple == (42, "123")

    def test_optional_coercion(self):
        """Test Optional type coercion."""

        class TestConstants(ConstantNamespace):
            """Test"""

            optional_int: Optional[int] = "42"  # type: ignore
            optional_none: Optional[int] = None

        assert TestConstants.optional_int == 42
        assert TestConstants.optional_none is None

    def test_nested_collection_coercion(self):
        """Test deeply nested type coercion."""

        class TestConstants(ConstantNamespace):
            """Test"""

            nested_list: list[list[int]] = [["1", "2"], ["3", "4"]]  # type: ignore
            nested_dict: dict[str, list[int]] = {1: ["1", "2"]}  # type: ignore

        assert TestConstants.nested_list == [[1, 2], [3, 4]]
        assert TestConstants.nested_dict == {"1": [1, 2]}


# =============================================================================
# Instantiation Tests
# =============================================================================


class TestConstantNamespaceInstantiation:
    """Test instantiation restrictions."""

    def test_cannot_instantiate(self):
        """Test that ConstantNamespace classes cannot be instantiated."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1

        with pytest.raises(ConstantsInstantiationError) as exc_info:
            TestConstants()

        assert "Cannot instantiate constant class 'TestConstants'" in str(
            exc_info.value
        )

    def test_cannot_instantiate_with_args(self):
        """Test that instantiation fails even with arguments."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1

        with pytest.raises(ConstantsInstantiationError):
            TestConstants()

        with pytest.raises(TypeError):
            TestConstants(1, 2, 3)  # type: ignore

        with pytest.raises(TypeError):
            TestConstants(arg1=1, arg2=2)  # type: ignore


# =============================================================================
# Modification Tests
# =============================================================================


class TestConstantNamespaceModification:
    """Test modification restrictions."""

    def test_cannot_modify_constants(self):
        """Test that constants cannot be modified."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1
            B: str = "hello"

        with pytest.raises(ConstantsModificationError) as exc_info:
            TestConstants.A = 2

        assert "Attribute 'A' of class 'TestConstants' cannot be modified" in str(
            exc_info.value
        )

    def test_cannot_add_new_attributes(self):
        """Test that new attributes cannot be added."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1

        with pytest.raises(ConstantsModificationError):
            TestConstants.NEW_ATTR = "new value"

    def test_mutable_objects_can_be_modified(self):
        """Test that mutable objects referenced by constants can still be modified.

        Note: This is intentional behavior - the reference is immutable, but the
        object itself is not. Users should use immutable types if they want complete
        immutability.
        """

        class TestConstants(ConstantNamespace):
            """Test"""

            my_list: list[int] = [1, 2, 3]
            my_dict: dict[str, int] = {"a": 1}

        # The reference cannot be changed, but the object itself can be modified
        TestConstants.my_list.append(4)
        assert TestConstants.my_list == [1, 2, 3, 4]

        TestConstants.my_dict["b"] = 2
        assert TestConstants.my_dict == {"a": 1, "b": 2}


# =============================================================================
# Composition Tests
# =============================================================================


class TestConstantNamespaceComposition:
    """Test composition rules and restrictions."""

    def test_cannot_define_init(self):
        """Test that __init__ cannot be defined."""
        with pytest.raises(ConstantsCompositionError) as exc_info:

            class TestConstants(ConstantNamespace):
                """Test"""

                A: int = 1

                def __init__(self):
                    pass

            _ = TestConstants.A

        assert "disallowed to have __new__ or __init__" in str(exc_info.value)

    def test_cannot_define_new(self):
        """Test that __new__ cannot be defined."""
        with pytest.raises(ConstantsCompositionError) as exc_info:

            class TestConstants(ConstantNamespace):
                """Test"""

                A: int = 1

                def __new__(cls):
                    pass

            _ = TestConstants.A

        assert "disallowed to have __new__ or __init__" in str(exc_info.value)

    def test_annotated_attribute_needs_value(self):
        """Test that annotated attributes must have values."""
        with pytest.raises(ConstantsCompositionError) as exc_info:

            class TestConstants(ConstantNamespace):
                """Test"""

                A: int  # Missing value

            _ = TestConstants.A

        assert "Attribute 'A' needs a value in constant class 'TestConstants'" in str(
            exc_info.value
        )


# =============================================================================
# Private Attributes Tests
# =============================================================================


class TestConstantNamespacePrivateAttributes:
    """Test handling of private attributes."""

    def test_private_attributes_excluded_by_default(self):
        """Test that private attributes are excluded by default.

        Note: The metaclass default is allow_private=False, so subclasses
        of ConstantNamespace exclude private attributes by default.
        """

        class TestConstants(ConstantNamespace):
            """Test"""

            _private: int = 1
            public: int = 2

        # Default behavior (allow_private=False in metaclass)
        assert "_private" not in TestConstants.__constants__
        assert "public" in TestConstants.__constants__
        assert len(TestConstants.__constants__) == 1

    def test_private_attributes_included_with_allow_private_true(self):
        """Test that private attributes can be included."""

        class TestConstants(ConstantNamespace, allow_private=True):
            """Test"""

            _private: int = 1
            public: int = 2

        assert "_private" in TestConstants.__constants__
        assert "public" in TestConstants.__constants__
        assert len(TestConstants.__constants__) == 2


# =============================================================================
# Introspection Tests
# =============================================================================


class TestConstantNamespaceIntrospection:
    """Test introspection methods."""

    test_constants: Any

    def setup_method(self):
        """Set up test constants."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A: int = 1
            B: str = "hello"
            C: float = 3.14

        self.test_constants = TestConstants

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.test_constants)
        assert "ConstantNamespace TestConstants" in repr_str
        assert "A=1" in repr_str
        assert "B='hello'" in repr_str
        assert "C=3.14" in repr_str

    def test_iter(self):
        """Test iteration over constants."""
        constants: list[str] = list(self.test_constants)  # type: ignore
        assert len(constants) == 3
        assert constants == ["A", "B", "C"]
        assert set(constants) == {"A", "B", "C"}

    def test_contains(self):
        """Test membership testing."""
        assert "A" in self.test_constants
        assert "B" in self.test_constants
        assert "C" in self.test_constants
        assert "D" not in self.test_constants

    def test_len(self):
        """Test length."""
        assert len(self.test_constants) == 3

    def test_items(self):
        """Test items method."""
        items = self.test_constants.items()
        assert len(items) == 3
        assert ("A", 1) in items
        assert ("B", "hello") in items
        assert ("C", 3.14) in items

    def test_keys(self):
        """Test keys method."""
        keys = self.test_constants.keys()
        assert set(keys) == {"A", "B", "C"}

    def test_values(self):
        """Test values method."""
        values = self.test_constants.values()
        assert set(values) == {1, "hello", 3.14}

    def test_get(self):
        """Test get method."""
        assert self.test_constants.get("A") == 1
        assert self.test_constants.get("B") == "hello"
        assert self.test_constants.get("NONEXISTENT") is None
        assert self.test_constants.get("NONEXISTENT", "default") == "default"

    def test_has_constant(self):
        """Test has_constant method."""
        assert self.test_constants.has_constant("A") is True
        assert self.test_constants.has_constant("B") is True
        assert self.test_constants.has_constant("NONEXISTENT") is False


# =============================================================================
# Inheritance Tests
# =============================================================================


class TestConstantNamespaceInheritance:
    """Test inheritance behavior."""

    def test_simple_inheritance(self):
        """Test basic inheritance."""

        class BaseConstants(ConstantNamespace):
            """Test"""

            A: int = 1
            B: str = "base"

        class DerivedConstants(BaseConstants):
            """Test"""

            C: float = 3.14
            B: str = "derived"  # Override

        assert DerivedConstants.A == 1
        assert DerivedConstants.B == "derived"
        assert DerivedConstants.C == 3.14
        assert "A" in DerivedConstants.__constants__
        assert "B" in DerivedConstants.__constants__
        assert "C" in DerivedConstants.__constants__

    def test_inheritance_instantiation_still_forbidden(self):
        """Test that inherited classes still cannot be instantiated."""

        class BaseConstants(ConstantNamespace):
            """Test"""

            A: int = 1

        class DerivedConstants(BaseConstants):
            """Test"""

            B: str = "hello"

        with pytest.raises(ConstantsInstantiationError):
            DerivedConstants()


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestConstantNamespaceEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_constants_attribute_when_no_annotations(self):
        """Test behavior when __constants__ is set but no annotations exist."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A = 1  # No annotation, so not a constant

        assert TestConstants.__constants__ == ()

    def test_constants_with_complex_types(self):
        """Test constants with complex type annotations."""

        class TestConstants(ConstantNamespace):
            """Test"""

            complex_list: list[dict[str, int]] = [{"a": 1}, {"b": 2}]

        assert TestConstants.complex_list == [{"a": 1}, {"b": 2}]
        assert "complex_list" in TestConstants.__constants__


# =============================================================================
# Helper Functions Tests
# =============================================================================


class TestHelperFunctions:
    """Test internal helper functions."""

    def test_verify_functions_with_init(self):
        """Test _verify_functions with __init__."""
        namespace: dict[str, Any] = {"__init__": lambda _: None}  # type: ignore

        with pytest.raises(ConstantsCompositionError):
            _verify_functions("TestClass", namespace)

    def test_verify_functions_with_new(self):
        """Test _verify_functions with __new__."""
        namespace: dict[str, Any] = {"__new__": lambda _: None}  # type: ignore

        with pytest.raises(ConstantsCompositionError):
            _verify_functions("TestClass", namespace)

    def test_verify_functions_without_restricted_methods(self):
        """Test _verify_functions without restricted methods."""
        namespace: dict[str, Any] = {"normal_method": lambda _: None}  # type: ignore

        # Should not raise
        _verify_functions("TestClass", namespace)

    def test_instantiation_error_function(self):
        """Test _instantiation_error helper function."""
        error_func = _instantiation_error("TestClass")

        with pytest.raises(ConstantsInstantiationError) as exc_info:
            error_func(None)

        assert "Cannot instantiate constant class 'TestClass'" in str(exc_info.value)


# =============================================================================
# Integration Tests
# =============================================================================


class TestConstantNamespaceIntegration:
    """Integration tests combining ConstantNamespace with the annotation registry."""

    def test_full_workflow_with_type_registry(self):
        """Test full workflow demonstrating integration with annotation registry.

        This test ensures that the ConstantNamespace properly uses the
        annotation registry system for type conversion.
        """

        class TestConstants(ConstantNamespace):
            """Test constants with various complex types."""

            A: int = "42"  # type: ignore
            B: list[int] = ["1", "2", "3"]  # type: ignore
            C: tuple[int, str] = (42, 123)  # type: ignore
            D: dict[str, int] = {1: "2"}  # type: ignore

        # All values should be properly coerced
        assert TestConstants.A == 42
        assert isinstance(TestConstants.A, int)

        assert TestConstants.B == [1, 2, 3]
        assert all(isinstance(x, int) for x in TestConstants.B)

        assert TestConstants.C == (42, "123")
        assert isinstance(TestConstants.C[0], int)
        assert isinstance(TestConstants.C[1], str)

        assert TestConstants.D == {"1": 2}

    def test_deeply_nested_conversion(self):
        """Test deeply nested type conversion in constants."""

        class TestConstants(ConstantNamespace):
            """Test"""

            complex_nested: dict[str, list[tuple[int, Optional[str]]]] = {
                1: [("1", "hello"), ("2", None)],
                2: [("3", "world")],
            }  # type: ignore

        expected: dict[str, Any] = {"1": [(1, "hello"), (2, None)], "2": [(3, "world")]}
        assert TestConstants.complex_nested == expected

    def test_all_type_features_combined(self):
        """Test combining all type features in one constant namespace."""

        class ComprehensiveConstants(ConstantNamespace):
            """Comprehensive test of all features."""

            # Basic types
            basic_int: int = 1
            basic_str: str = "hello"
            basic_float: float = 3.14

            # Type coercion
            coerced_int: int = 3.14  # type: ignore
            coerced_str: str = 123  # type: ignore

            # Collections
            list_val: list[int] = [1, 2, 3]
            tuple_val: tuple[int, str] = (1, "a")
            dict_val: dict[str, int] = {"a": 1}
            set_val: set[int] = {1, 2, 3}

            # Nested collections
            nested: list[dict[str, int]] = [{"a": 1}]

            # Union types
            union_val: int | str = "hello"

            # Optional types
            optional_val: Optional[int] = None

            # Special wrappers
            final_val: Final[int] = 42
            classvar_val: ClassVar[int] = 100

            # Path
            path_val: Path = "documents/file.txt"  # type: ignore

        # Verify all are correctly set
        assert ComprehensiveConstants.basic_int == 1
        assert ComprehensiveConstants.coerced_int == 3
        assert ComprehensiveConstants.list_val == [1, 2, 3]
        assert ComprehensiveConstants.union_val == "hello"
        assert ComprehensiveConstants.optional_val is None
        assert ComprehensiveConstants.path_val == Path("documents/file.txt")
