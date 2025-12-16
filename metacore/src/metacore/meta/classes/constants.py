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
Description: This module provides tools to create namespaces (class) of constants.
🦙
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from collections.abc import Iterator
from typing import Any, NoReturn, Callable, ClassVar
from ...abstract.exceptions.traced_exceptions import TracedException
from ..typing_utilities.utilities import resolve_annotation_types
from ..typing_utilities.annotations_processors.processors import (
    annotation_registry,
)


class ConstantsInstantiationError(TracedException):
    """Instantiation error of a Constants class."""


class ConstantsCompositionError(TracedException):
    """Composition error of a Constants class."""


class ConstantsModificationError(TracedException):
    """Modification error of a Constants class."""


def _verify_functions(name: str, namespace: dict[str, Any]) -> None:
    """Verify that no disalowed function is added.
    Disallowed functions are __new__ and __init__.

    Args:
        name (str): name of the class.
        namespace (dict[str, Any]): namespace of the class.

    Raises:
        ConstantsCompositionError: Raised when a disallowed function is added.
    """
    if "__init__" in namespace or "__new__" in namespace:
        raise ConstantsCompositionError(
            f"Constant class '{name}' is disallowed to have __new__ or __init__"
            " method since it shall never be instantiated."
        )


def _instantiation_error(name: str) -> Callable[[Any], NoReturn]:
    """Helper to format an error message when trying to instantiate a Constants class.

    Args:
        name (str): name of the class.

    Returns:
        Callable[[], NoReturn]: A callable that throws an instantiation error when called.
    """

    def f(_: Any) -> NoReturn:
        raise ConstantsInstantiationError(
            f"Cannot instantiate constant class '{name}'. Constant class cannot be instantiated."
        )

    return f


def _verify_annotations_and_coerce(
    name: str, namespace: dict[str, Any]
) -> None:
    """Verify that no annotated member value is missing and coerce all annotated type.

    Args:
        name (str): name of the class.
        namespace (dict[str, Any]): namespace of the class.

    Raises:
        ConstantsCompositionError: Raised when an annotated member value is missing.
    """
    if "__annotations__" in namespace:
        annotations = resolve_annotation_types(namespace["__annotations__"])
        for key in annotations:
            if key not in namespace["__constants__"]:
                continue
            # Ensure that any annotated member has a value.
            if key not in namespace:
                raise ConstantsCompositionError(
                    f"Attribute '{key}' needs a value in constant class '{name}'."
                )

            # coerce type
            try:
                registry = annotation_registry()
                namespace[key] = registry.convert_to_annotation(
                    annotations[key], namespace[key]
                )
            except Exception as e:
                raise ConstantsCompositionError(
                    f"Failed to coerce value {namespace[key]!r} to type {annotations[key]} "
                    f"for constant '{key}' in class '{name}': {e}"
                ) from e

class ConstantsMetaclass(type):
    __constants__: tuple[str, ...]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        allow_private: bool = False,
        **kwargs: Any,
    ) -> Any:

        # verify that no function is added.
        _verify_functions(name, namespace)

        # add an __new__ method that throws an error.
        namespace["__new__"] = _instantiation_error(name)

        # create a tuple of constant names for introspection.
        namespace["__constants__"] = (
            tuple(
                k
                for k in namespace["__annotations__"]
                if allow_private or not k.startswith("_")
            )
            if "__annotations__" in namespace
            else ()
        )

        # add superclasses names
        for base in bases:
            if isinstance(base, ConstantsMetaclass) and reversed(base.__constants__):
                constants_names = list(base.__constants__)
                existing = set(base.__constants__)
                constants_names.extend(
                    k for k in namespace["__constants__"] if k not in existing
                )
                namespace["__constants__"] = tuple(constants_names)

        # verify that no annotated member is missing and coerce annotated types.
        _verify_annotations_and_coerce(name, namespace)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls

    def __setattr__(cls, name: str, value: Any) -> NoReturn:
        raise ConstantsModificationError(
            f"Attribute '{name}' of class '{cls.__name__}' cannot be modified. Reason: Constant"
            " class cannot be modified."
        )

    def __repr__(cls) -> str:
        """Returns a string representation of the class."""
        constants = ", ".join(f"{k}={getattr(cls, k)!r}" for k in cls.__constants__)
        return f"<ConstantNamespace {cls.__name__}({constants})>"

    def __iter__(cls) -> Iterator[str]:
        return iter(cls.__constants__)

    def __contains__(cls, name: str) -> bool:
        """Check if a constant name exists."""
        return name in cls.__constants__

    def __len__(cls) -> int:
        """Return the number of constants."""
        return len(cls.__constants__)

    def items(cls) -> list[tuple[str, Any]]:
        """Return all constants as (name, value) pairs."""
        return [(k, getattr(cls, k)) for k in cls.__constants__]

    def keys(cls) -> tuple[str, ...]:
        """Return all constant names."""
        return cls.__constants__

    def values(cls) -> tuple[Any, ...]:
        """Return all constant values."""
        return tuple(getattr(cls, k) for k in cls.__constants__)

    def get(cls, name: str, default: Any = None) -> Any:
        """Get a constant value with optional default."""
        return getattr(cls, name, default)

    def has_constant(cls, name: str) -> bool:
        """Check if a constant exists."""
        return name in cls.__constants__


class ConstantNamespace(metaclass=ConstantsMetaclass, allow_private=False):
    """Base class to create namespaces (class) of constants.
    Examples:
        >>> class MyConstants(ConstantNamespace):
        ...    A = 1 # this is not a constant. It needs annotation.
        ...    _A: int = 1 # this is not a constant unless allow_private=True.
        ...    B: int = 2 # this is a constant.
        ...    C: int = 3.4 # will result in 3. Values are coerced.
        ...    path: pathlib.Path = "documents/test.txt" # coerced to a Path.
        ...    l: list[int] = [1, 1.5, 3] # coerced to [1, 1, 3].

        >>> MyConstants.B
        2

        >>> MyConstants.C = 3.4 # raises ConstantsModificationError.

        >>> MyConstants.l = [] # raises ConstantsModificationError.

        >>> MyConstants.l.clear() # Does not raise, it is the user's
        ...                       # responsibility to use unmutable types.
    """

    __constants__: ClassVar[tuple[str, ...]]
