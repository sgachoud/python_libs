"""Type annotation utility functions.

This module provides helper functions for working with Python type annotations,
including utilities for checking union types, optional types, and resolving
forward references in annotations.
"""
from typing import (
    Annotated, Any, Callable, Literal, TypeAliasType, TypeVar, cast, Union,
    get_origin, get_args, get_type_hints,
)
from collections.abc import Callable as CallableOrigin
from types import UnionType, NoneType
import sys

from .exceptions import AnnotationProcessorError

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
    return get_type_hints(X, globalns=nglobals, localns=nlocals, include_extras=True)


def _substitute_alias_parameters(annotation: Any, substitutions: dict[Any, Any]) -> Any:
    """Substitute alias type parameters without interpreting metadata as types."""
    if isinstance(annotation, TypeVar):
        return substitutions.get(annotation, annotation)
    origin = get_origin(annotation)
    if origin is None or origin is Literal:
        return annotation
    args = get_args(annotation)
    if not args:
        return annotation
    if origin is Annotated:
        return Annotated[_substitute_alias_parameters(args[0], substitutions), *args[1:]]
    if origin is CallableOrigin:
        parameters, result = args
        if parameters is not Ellipsis:
            parameters = [_substitute_alias_parameters(arg, substitutions) for arg in parameters]
        return cast(Any, Callable)[
            parameters, _substitute_alias_parameters(result, substitutions)
        ]
    resolved = tuple(_substitute_alias_parameters(arg, substitutions) for arg in args)
    if origin in (Union, UnionType):
        return Union[resolved]
    return origin[resolved]


def _expand_type_alias(annotation: Annotation) -> Annotation:
    """Expand a plain or specialized generic alias by one level."""
    alias = get_origin(annotation) or annotation
    if not isinstance(alias, TypeAliasType):
        return annotation
    parameters = alias.__type_params__
    arguments = get_args(annotation)
    if len(parameters) != len(arguments):
        raise AnnotationProcessorError(
            f"Type alias '{alias}' requires {len(parameters)} type arguments;"
            f" received {len(arguments)}."
        )
    expanded = _substitute_alias_parameters(alias.__value__, dict(zip(parameters, arguments)))
    module = sys.modules.get(alias.__module__ or "")
    nglobals = module.__dict__ if module is not None else None
    return resolve_annotation_types({"_": expanded}, nglobals=nglobals)["_"]


def _reject_recursive_aliases(annotation: Annotation) -> None:
    """Check alias definitions, including branches unused by a default factory."""
    checked: set[TypeAliasType] = set()

    def visit(value: Any, active: frozenset[TypeAliasType]) -> None:
        origin = get_origin(value)
        alias = origin or value
        if isinstance(alias, TypeAliasType):
            if alias in active:
                raise AnnotationProcessorError(
                    f"Recursive type aliases are not supported: {alias}."
                )
            if alias not in checked:
                module = sys.modules.get(alias.__module__ or "")
                namespace = module.__dict__ if module is not None else None
                body = resolve_annotation_types({"_": alias.__value__}, namespace)["_"]
                visit(body, active | {alias})
                checked.add(alias)
            for argument in get_args(value):
                visit(argument, active)
            return
        if origin is Literal:
            return
        args = get_args(value)
        if origin is Annotated:
            args = args[:1]
        for argument in args:
            if isinstance(argument, list):
                for parameter in argument:
                    visit(parameter, active)
            else:
                visit(argument, active)

    visit(annotation, frozenset())


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
