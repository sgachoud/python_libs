"""
Author: Sébastien Gachoud
Created: 2025-07-11
Description: This module provides tools to create namespaces (class) of constants.
🦙
"""

__author__ = "Sébastien Gachoud"
__version__ = "1.0.0"
__license__ = "MIT"

from typing import Any, NoReturn, Callable, get_origin
from types import UnionType
from ...abstract.exceptions.traced_exceptions import TracedException
from ..typing.general import type_hints_from_dict


class ConstantsInstantiationError(TracedException):
    """Instantiation error of a Constants class."""


class ConstantsCompositionError(TracedException):
    """Composition error of a Constants class."""


class ConstantsModificationError(TracedException):
    """Modification error of a Constants class."""


def verify_functions(name: str, namespace: dict[str, Any]) -> None:
    """Verify that no dissalowed function is added.
    Dissallowed functions are __new__ and __init__.

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


def instantiation_error(name: str) -> Callable[[Any], NoReturn]:
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


def verify_annotations(name: str, namespace: dict[str, Any]) -> None:
    """Verify that:
    - no annotated member value is missing.
    - all annotated type are true types (not type checking annotations).

    Args:
        name (str): name of the class.
        namespace (dict[str, Any]): namespace of the class.

    Raises:
        ConstantsCompositionError: Raised when an annotated member value is missing.
    """
    if "__annotations__" in namespace:
        annotations = type_hints_from_dict(namespace["__annotations__"])
        for key in annotations:
            if key not in namespace:
                raise ConstantsCompositionError(
                    f"Attribute '{key}' needs a value in constant class '{name}'."
                )

            type_hint = annotations[key]
            if not isinstance(type_hint, type) and (
                (o := get_origin(type_hint)) is None or o is UnionType
            ):
                raise ConstantsCompositionError(
                    f"Attribute '{key}' of constant class '{name}' needs to have a true type."
                )


class _ConstantsMetaclass(type):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwargs: Any,
    ) -> Any:

        # verify that no function is added.
        verify_functions(name, namespace)

        # add an __new__ method that throws an error.
        namespace["__new__"] = instantiation_error(name)

        # verify that no annotated member is missing.
        verify_annotations(name, namespace)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls

    def __setattr__(cls, name: str, value: Any) -> NoReturn:
        raise ConstantsModificationError(
            f"Attribute '{name}' of class '{cls.__name__}' cannot be modified. Reason: Constant"
            " class cannot be modified."
        )


class ConstantNamespace(metaclass=_ConstantsMetaclass):
    """Base class to create namespaces (class) of constants."""
