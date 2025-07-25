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
Description: Tests for the constants module.
🦙

Note: written with the assistance of ChatGPT from OpenAI and Claude AI.
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from pathlib import Path
from typing import Any, Dict, List

import pytest

from sg_lib.src.sg_lib.meta.classes.constants import (
    ConstantNamespace,
    ConstantsCompositionError,
    ConstantsInstantiationError,
    ConstantsModificationError,
    _instantiation_error,  # type: ignore
    _verify_functions,  # type: ignore
)


### ChatGPT ###
def test_instantiation_raises_error():
    """Test"""

    class MyConstants(ConstantNamespace):
        """Test"""

        A: int = 1

    with pytest.raises(ConstantsInstantiationError):
        _ = MyConstants()


def test_missing_annotation_value_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int

        _ = BadConstants.A


def test_type_cohercion():
    """Test"""

    class BadConstants(ConstantNamespace):
        """Test"""

        A: int | str = "1"
        B: int = 1.5  # type: ignore
        C: int | float | str = 1
        D: Path = "documents/test.txt"  # type: ignore

    assert BadConstants.A == "1"
    assert BadConstants.B == 1
    assert BadConstants.C == 1
    assert BadConstants.D == Path("documents/test.txt")


def test_adding_init_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int = 1

            def __init__(self):
                pass

        _ = BadConstants.A


def test_adding_new_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int = 1

            def __new__(cls):
                pass

        _ = BadConstants.A


def test_modifying_constant_raises_modification_error():
    """Test"""

    class MyConstants(ConstantNamespace):
        """Test"""

        A: int = 1

    with pytest.raises(ConstantsModificationError):
        MyConstants.A = 2


def test_valid_constant_class_creation():
    """Test"""

    class GoodConstants(ConstantNamespace):
        """Test"""

        A: int = 1
        B: str = "hello"

    assert GoodConstants.A == 1
    assert GoodConstants.B == "hello"


### Claude


class TestConstantNamespaceBasic:
    """Test basic functionality of ConstantNamespace."""

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

    def test_type_coercion(self):
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

    def test_type_coercion_first_in_union(self):
        """Test that values are coerced to their annotated types, even with first_in_union."""

        class TestConstants(ConstantNamespace, first_in_union=True):
            """Test"""

            int_value: int | float = 3.14  # Should be coerced to 3
            str_value: str | int = 123  # Should be coerced to "123"
            float_value: float = 5  # Should be coerced to 5.0

        assert TestConstants.int_value == 3
        assert isinstance(TestConstants.int_value, int)
        assert TestConstants.str_value == "123"
        assert isinstance(TestConstants.str_value, str)
        assert TestConstants.float_value == 5.0
        assert isinstance(TestConstants.float_value, float)

    def test_path_coercion(self):
        """Test coercion to pathlib.Path."""

        class TestConstants(ConstantNamespace):
            """Test"""

            path: Path = "documents/test.txt"  # type: ignore

        assert isinstance(TestConstants.path, Path)
        assert TestConstants.path == Path("documents/test.txt")

    def test_list_coercion(self):
        """Test coercion to typed lists."""

        class TestConstants(ConstantNamespace):
            """Test"""

            int_list: List[int] = [1, 1.5, 3]  # type: ignore

        assert TestConstants.int_list == [1, 1, 3]
        assert all(isinstance(x, int) for x in TestConstants.int_list)

    def test_unannotated_attributes_not_constants(self):
        """Test that unannotated attributes are not considered constants."""

        class TestConstants(ConstantNamespace):
            """Test"""

            A = 1  # Not a constant (no annotation)
            B: int = 2  # This is a constant

        assert "A" not in TestConstants.__constants__
        assert "B" in TestConstants.__constants__
        assert TestConstants.__constants__ == ("B",)


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
        """Test that mutable objects referenced by constants can still be modified."""

        class TestConstants(ConstantNamespace):
            """Test"""

            my_list: List[int] = [1, 2, 3]
            my_dict: Dict[str, int] = {"a": 1}

        # The reference cannot be changed, but the object itself can be modified
        TestConstants.my_list.append(4)
        assert TestConstants.my_list == [1, 2, 3, 4]

        TestConstants.my_dict["b"] = 2
        assert TestConstants.my_dict == {"a": 1, "b": 2}


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

    def test_type_coercion_failure(self):
        """Test handling of type coercion failures."""
        with pytest.raises(ConstantsCompositionError) as exc_info:

            class TestConstants(ConstantNamespace):
                """Test"""

                A: int = "not_convertible_to_int"  # type: ignore

            _ = TestConstants.A

        assert "Failed to coerce value" in str(exc_info.value)
        assert "to type" in str(exc_info.value)


class TestConstantNamespacePrivateAttributes:
    """Test handling of private attributes."""

    def test_private_attributes_included_by_default(self):
        """Test that private attributes are included by default."""

        class TestConstants(ConstantNamespace):
            """Test"""

            _private: int = 1
            public: int = 2

        assert "_private" in TestConstants.__constants__
        assert "public" in TestConstants.__constants__
        assert len(TestConstants.__constants__) == 2

    def test_private_attributes_excluded_with_allow_private_false(self):
        """Test that private attributes can be excluded."""

        class TestConstants(ConstantNamespace, allow_private=False):
            """Test"""

            _private: int = 1
            public: int = 2

        assert "_private" not in TestConstants.__constants__
        assert "public" in TestConstants.__constants__
        assert len(TestConstants.__constants__) == 1


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


class TestHelperFunctions:
    """Test helper functions."""

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


class TestConstantNamespaceEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_constant_namespace(self):
        """Test empty constant namespace."""

        class EmptyConstants(ConstantNamespace):
            """Test"""

        assert len(EmptyConstants.__constants__) == 0
        assert not list(EmptyConstants)  # type: ignore
        assert EmptyConstants.items() == []

    def test_no_annotations_but_has_constants_attribute(self):
        """Test behavior when __constants__ is manually defined."""

        # This is testing the metaclass behavior when __annotations__ is not present
        class TestConstants(ConstantNamespace):
            """Test"""

            A = 1  # No annotation, so not a constant

        assert TestConstants.__constants__ == ()

    def test_constants_with_complex_types(self):
        """Test constants with complex type annotations."""

        class TestConstants(ConstantNamespace):
            """Test"""

            complex_list: List[Dict[str, int]] = [{"a": 1}, {"b": 2}]

        assert TestConstants.complex_list == [{"a": 1}, {"b": 2}]
        assert "complex_list" in TestConstants.__constants__
