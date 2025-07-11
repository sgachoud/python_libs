"""
Author: Sébastien Gachoud
Created: 2025-07-11
Description: This module provides tools to create namespaces (class) of constants.
🦙
"""

__author__ = "Sébastien Gachoud"
__version__ = "1.0.0"
__license__ = "MIT"

from typing import Any, NoReturn, Callable
from ...abstract.exceptions.traced_exceptions import TracedException


class ConstantsInstantiationError(TracedException):
    """Instantiation error of a Constants class."""


class ConstantsCompositionError(TracedException):
    """Composition error of a Constants class."""


class ConstantsModificationError(TracedException):
    """Modification error of a Constants class."""


def instantiation_error(name: str) -> Callable[[], NoReturn]:
    """Helper to format an error message when trying to instantiate a Constants class.

    Args:
        name (str): name of the class.

    Returns:
        Callable[[], NoReturn]: A callable that throws an instantiation error when called.
    """

    def f() -> NoReturn:
        raise ConstantsInstantiationError(
            f"Cannot instantiate constant class '{name}'. Constant class cannot be instantiated."
        )

    return f


def verify_annotations(name: str, namespace: dict[str, Any]) -> None:
    """Verify that no annotated member value is missing.

    Args:
        name (str): name of the class.
        namespace (dict[str, Any]): namespace of the class.

    Raises:
        ConstantsCompositionError: _description_
    """
    if "__annotations__" in namespace:
        for key in namespace["__annotations__"]:
            if key not in namespace:
                raise ConstantsCompositionError(
                    f"Attribute '{key}' needs a value in constant class '{name}'."
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
        if "__init__" in namespace:
            raise ConstantsCompositionError(
                "Constant class is disallowed to have __init__ method since it shall never be"
                " instantiated."
            )
        namespace["__init__"] = instantiation_error(name)

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
