"""Tests for public annotation inspection helpers."""

from typing import Any, Optional, Union

from metacore.typing import (
    Implement,
    is_union,
    is_optional,
    is_binary_optional,
    resolve_annotation_types,
)


def test_implement_does_not_add_the_declared_type_to_the_mro():
    class Interface:
        pass

    class Concrete(Implement(Interface)):
        pass

    assert Concrete.__bases__ == (object,)
    assert not isinstance(Concrete(), Interface)


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
