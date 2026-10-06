"""Type annotation utility functions.

This module provides helper functions for working with Python type annotations,
including utilities for checking union types, optional types, and resolving
forward references in annotations.
"""
from typing import Any, cast, Union, get_origin, get_args, get_type_hints
from types import UnionType, NoneType

type Annotation = Any

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


def resolve_annotation_types(
    annotations: dict[str, Any],
    nglobals: dict[str, Any] | None = None,
    nlocals: dict[str, Any] | None = None,
) -> dict[str, Annotation]:
    """
    Get type hints from a dictionary of annotations. See typing.get_type_hints.

    This function is useful when you want to get the type hints from a dictionary
    of annotations instead of a class or a function.

    Args:
        annotations (dict[str, Any]): A dictionary of annotations.
        nglobals (dict[str, Any] | None): Globals to resolve forward refs against.
        nlocals (dict[str, Any] | None): Locals to resolve forward refs against.

    Returns:
        dict[str, Any]: A dictionary of type hints.
    """
    X = type("X", (), {"__annotations__": annotations})
    return get_type_hints(X, globalns=nglobals, localns=nlocals)


class _ImplementMeta(type):
    def __new__(mcls, name, bases, namespace):
        if bases:
            bases = tuple(base for base in bases if base is not _Implement)
        return super().__new__(mcls, name, bases, namespace)


class _Implement(metaclass=_ImplementMeta):
    pass


class Implement[T]:
    """Use to trick the type checker that a class inherits from another class without actually doing so.
    class Cat:
      def meow(self): print("meow")

    class FakeCat(Implement(Cat)):
      def __getattr__(self, name: str):
        if name == "meow":
          return lambda: print("meow")

    fc = FakeCat()
    fc.meow() # type checker recognizes fc to have the meow method of Cat.
    print(fc.mro()) # mro does not contain Cat.
    """

    def __new__(cls, _: type[T]) -> type[T]:
        return cast(type[T], _Implement)


__all__ = [
    "Annotation",
    "Implement",
    "is_union",
    "is_optional",
    "is_binary_optional",
    "resolve_annotation_types",
]
