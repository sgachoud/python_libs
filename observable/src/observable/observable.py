"""
MIT License

Copyright (c) 2026 Sébastien Gachoud

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
Created: 2026-10-05
Description: This module provides observable fields and change notifications.
🦙
"""

from __future__ import annotations

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

import sys
from copy import copy
from dataclasses import dataclass
from enum import IntFlag
from enum import auto as e_auto
from typing import (
    Any,
    Callable,
    Self,
    TypeVar,
    overload,
    get_args,
    get_origin,
    cast,
)

import numpy as np

from metacore import TracedException, annotation_registry
from metacore.annotations import AnnotationsRegistry
from metacore.typing import resolve_annotation_types

type Observer = Callable[..., Any]


class ObservableFieldError(TracedException):
    """Base error for observable field definitions and access."""


class UninitializedError(ObservableFieldError):
    """A field has neither a stored value nor a default."""


class MemberDefinitionError(ObservableFieldError):
    """An observable member has an invalid definition."""


class TypeFormatError(ObservableFieldError):
    """A field annotation has an unsupported format."""


class DefaultValueError(ObservableFieldError):
    """A field default cannot be constructed."""


class AccessViolationError(ObservableFieldError):
    """A field operation violates its access policy."""


class ReadAccessViolationError(AccessViolationError):
    """Reading the field is forbidden."""


class WriteAccessViolationError(AccessViolationError):
    """Writing the field is forbidden."""


class PropertyDefinitionError(ObservableFieldError):
    """An observable property has an invalid definition."""


class GetterDefinitionError(ObservableFieldError):
    """An observable getter has an invalid definition."""


class SetterDefinitionError(ObservableFieldError):
    """An observable setter has an invalid definition."""


class Access(IntFlag):
    """Access policy of an observable field.

    Attributes:
        none (int): No access. The field cannot be written or read. This can be
          useful to have a notification only field. All fields can be observed.
        read (int): Read access. Allows the field to be read.
        write (int): Write access. Allows the field to be written.
    """

    # Lowercase flag names are part of the public Access.read / Access.write API.
    # pylint: disable=invalid-name
    none = 0
    read = e_auto()
    write = e_auto()
    both = read | write
    r = read
    w = write
    rw = read | write


class Empty:
    """Represent a value not provided."""

    def __new__(cls) -> type[Empty]:
        return Empty

    def __repr__(self) -> str:
        return "Observably Empty"

    def __bool__(self) -> bool:
        return False


class Auto:
    """Request the default to be automatically derived from the field's type annotation."""

    def __new__(cls) -> type[Auto]:
        return Auto

    def __repr__(self) -> str:
        return "Observably Auto"


class ObservableFieldDecorators[T, I]:
    """Collect callbacks declared with field decorators."""

    convert: Callable[[I], T] | None = None
    compare: Callable[[T, T], bool] | None = None
    assign: Callable[[Observable, T], None] | None = None
    set: Callable[[Observable, I], None] | None = None
    get: Callable[[Observable], T] | None = None

    def converter(self, converter: Callable[[I], T]) -> Callable[[I], T]:
        """Register a conversion callback and return it unchanged."""
        self.convert = converter
        return converter

    def comparator(self, comparator: Callable[[T, T], bool]) -> Callable[[T, T], bool]:
        """Register the comparison used to suppress unchanged-value notifications."""
        self.compare = comparator
        return comparator

    def assigner[S: Observable](
        self, assigner: Callable[[S, T], None]
    ) -> Callable[[S, T], None]:
        """Register the callback that stores a converted value."""
        self.assign = cast(Callable[[Observable, T], None], assigner)
        return assigner

    def setter[S: Observable](
        self, setter: Callable[[S, I], None]
    ) -> Callable[[S, I], None]:
        """Register a callback that replaces the default setter."""
        self.set = cast(Callable[[Observable, I], None], setter)
        return setter

    def getter[S: Observable](self, getter: Callable[[S], T]) -> Callable[[S], T]:
        """Register a callback that replaces the default getter."""
        self.get = cast(Callable[[Observable], T], getter)
        return getter


@dataclass
class AutoField[T, I = T](ObservableFieldDecorators[T, I]):
    """Field configuration whose types are supplied by the class annotation."""

    # The configuration exposes each independent descriptor option explicitly.
    # pylint: disable=too-many-instance-attributes
    default: T | type[Empty] | type[Auto] = Empty
    default_factory: Callable[[], T] | None = None
    access: Access = Access.both
    custom_annotation_registry: AnnotationsRegistry | None = None
    force_type: tuple[Any, Any] | type[Empty] = Empty
    convert: Callable[[I], T] | None = None
    compare: Callable[[T, T], bool] | None = None
    assign: Callable[[Observable, T], None] | None = None
    set: Callable[[Observable, I], None] | None = None
    get: Callable[[Observable], T] | None = None

    def as_observable_field(self) -> ObservableField[T, I]:
        """Build a descriptor with this configuration and its callbacks."""
        return ObservableField[T, I](
            default=self.default,
            default_factory=self.default_factory,
            access=self.access,
            custom_annotation_registry=self.custom_annotation_registry,
            force_type=self.force_type,
            converter=self.convert,
            comparator=self.compare,
            assigner=self.assign,
            setter=self.set,
            getter=self.get,
        )


# Keep the existing positional API for the independent descriptor options.
# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def auto_field[T, I = T](
    default: T | type[Empty] | type[Auto] = Empty,
    default_factory: Callable[[], T] | None = None,
    access: Access = Access.both,
    custom_annotation_registry: AnnotationsRegistry | None = None,
    force_type: tuple[Any, Any] | type[Empty] = Empty,
    converter: Callable[[I], T] | None = None,
    comparator: Callable[[T, T], bool] | None = None,
    assigner: Callable[[Observable, T], None] | None = None,
    setter: Callable[[Observable, I], None] | None = None,
    getter: Callable[[Observable], T] | None = None,
) -> Any:
    """Declare a field; the metaclass replaces this configuration with a descriptor.

    The return type permits assignment to an ObservableField annotation while the
    runtime configuration retains the decorator methods used in the class body.
    """
    return AutoField(
        default,
        default_factory,
        access,
        custom_annotation_registry,
        force_type,
        converter,
        comparator,
        assigner,
        setter,
        getter,
    )


class ObservableField[T, I = T](ObservableFieldDecorators[T, I]):
    """Descriptor that converts values, controls access, and notifies observers."""

    # Each callback and resolved field option is stored independently.
    # pylint: disable=too-many-instance-attributes
    # Keep the existing constructor's positional API.
    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        default: T | type[Empty] | type[Auto] = Empty,
        default_factory: Callable[[], T] | None = None,
        access: Access = Access.both,
        custom_annotation_registry: AnnotationsRegistry | None = None,
        force_type: tuple[Any, Any] | type[Empty] = Empty,
        converter: Callable[[I], T] | None = None,
        comparator: Callable[[T, T], bool] | None = None,
        assigner: Callable[[Observable, T], None] | None = None,
        setter: Callable[[Observable, I], None] | None = None,
        getter: Callable[[Observable], T] | None = None,
    ) -> None:

        if default is not Empty and default_factory is not None:
            raise ValueError(
                "default_value and default_factory can not be provided at the same time."
            )

        self.__post_value = (
            default,
            force_type,
            converter,
            comparator,
            assigner,
            setter,
            getter,
        )

        self.default_factory = default_factory
        self._registry = custom_annotation_registry or annotation_registry()
        self.access = access

        self.name = "Undefined"

    def __post_init__(self) -> None:
        default_value, force_type, converter, comparator, assigner, setter, getter = (
            self.__post_value
        )
        del self.__post_value
        if isinstance(force_type, tuple):
            _type, input_types = force_type
        elif (orig_class := getattr(self, "__orig_class__", None)) is not None:
            _type, input_types = get_args(orig_class)
            if isinstance(input_types, TypeVar):
                input_types = _type
        else:
            raise ValueError(
                "ObservableField must be used with an Observable class. If you think it is done "
                "properly but still fails, please open an issue on github. To bypass this error, "
                "you can provide "
                "the type and input types manually through force_type."
            )
        self.default = self.__make_default(default_value, self.default_factory, _type)
        self.type = _type
        self.input_types = input_types

        self.default_convert: Callable[[I], T] = (
            self._registry.converter_from_annotation(_type)
        )
        self._converter: Callable[[I], T] = converter or self.default_convert
        self._comparator: Callable[[Any, Any], bool] = (
            comparator or self.default_compare
        )
        self._assigner: Callable[[Observable, T], None] = (
            assigner or self.default_assign
        )
        self._setter: Callable[[Observable, I], None] = setter or self.default_set
        self._getter: Callable[[Observable], T] = getter or self.default_get

    def __make_default(
        self,
        default: T | type[Empty] | type[Auto],
        factory: Callable[[], T] | None,
        annotation: Any,
    ) -> T | type[Empty]:
        if default is Auto:
            return self._registry.default_annotation(annotation)
        if default is not Empty:
            return cast(T, default)
        if factory is not None:
            return factory()
        return Empty

    def default_compare(self, value1: Any, value2: Any) -> bool:
        """Compare scalar or NumPy values for equality."""
        if isinstance(value1, np.ndarray) or isinstance(value2, np.ndarray):
            return np.array_equal(value1, value2)
        return value1 == value2

    def default_assign(self, instance: Observable, value: T) -> None:
        """Store a converted value in the owning instance."""
        # The descriptor and its owner share the module's internal storage protocol.
        # pylint: disable=protected-access
        instance._observable_values[self] = value

    def default_set(self, instance: Observable, value: I) -> None:
        """Convert and store an input, notifying observers when its value changes."""
        # pylint: disable=protected-access
        new_value = self._converter(value)
        if self in instance._observable_values and self._comparator(
            instance._observable_values[self], new_value
        ):
            return
        self._assigner(instance, new_value)
        instance.notify(self, value)

    def default_get(self, instance: Observable) -> T:
        """Return the stored value or default, enforcing the read policy."""
        # pylint: disable=protected-access
        if Access.read not in self.access:
            raise ReadAccessViolationError(
                f"Cannot read attribute '{self.name}', read is not allowed."
            )
        if Access.write not in self.access:
            if self.default is not Empty:
                return cast(T, self.default)
            raise UninitializedError(
                f"Attribute '{self.name}' has not value and is not writable."
            )
        if self in instance._observable_values:
            return instance._observable_values[self]
        if self.default is not Empty:
            return cast(T, self.default)
        raise UninitializedError(f"Attribute '{self.name}' is not initialized.")

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, instance: None, owner: type, /) -> Self: ...
    @overload
    def __get__(
        self, instance: Observable, owner: type[Observable] | None = None, /
    ) -> T: ...

    def __get__(
        self, instance: Observable | None, owner: type[Observable] | None = None
    ) -> T | Self:
        if instance is None:
            return self
        return self._getter(instance)

    def __set__(self, instance: Observable, value: I) -> None:
        if Access.write not in self.access:
            raise WriteAccessViolationError(
                f"Cannot write attribute '{self.name}', write is not allowed."
            )
        self._setter(instance, value)


class ObservableMeta(type):
    """Resolve field declarations and collect inherited descriptors."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwargs: Any,
    ) -> ObservableMeta:
        fields = mcs._collect_observable_fields(bases, namespace)
        # Inherited descriptors have already been finalized by their declaring class.
        for value in namespace.values():
            if isinstance(value, ObservableField):
                value.__post_init__()
        mcs._populate_observables(namespace, fields)
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    @classmethod
    def _collect_observable_fields(
        mcs, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> dict[str, ObservableField[Any, Any]]:
        # The metaclass collects the same private field map that it creates below.
        # pylint: disable=protected-access
        fields: dict[str, ObservableField[Any, Any]] = {}
        for base in bases:
            if hasattr(base, "_observable_fields"):
                fields.update(base._observable_fields)
        for name, value in namespace.items():
            if isinstance(value, ObservableField):
                fields[name] = value
            if isinstance(value, AutoField):
                fields[name] = mcs._process_auto_field(namespace, name, value)
                namespace[name] = fields[name]
        return fields

    @classmethod
    def _process_auto_field(
        mcs, namespace: dict[str, Any], name: str, field: AutoField[Any, Any]
    ) -> ObservableField[Any, Any]:
        annotation = namespace.get("__annotations__", {}).get(name, None)
        if annotation is None:
            raise TypeError(f"Automatic field '{name}' must have a type annotation.")
        module = sys.modules.get(namespace.get("__module__", ""))
        nglobals = module.__dict__ if module is not None else None
        annotation = resolve_annotation_types({name: annotation}, nglobals, namespace)[
            name
        ]
        orig = get_origin(annotation)
        if orig is None or orig is not ObservableField:
            raise TypeError(
                f"Automatic field '{name}' must be annotated as an ObservableField."
            )
        of = field.as_observable_field()
        setattr(of, "__orig_class__", annotation)
        return of

    @classmethod
    def _populate_observables(
        mcs,
        namespace: dict[str, Any],
        fields: dict[str, ObservableField[Any, Any]],
    ) -> None:
        namespace["_observable_fields"] = fields


class Observable(metaclass=ObservableMeta):
    """Owner of observable values and per-instance observer subscriptions."""

    _observable_fields: dict[str, ObservableField[Any, Any]]
    _observable_values: dict[ObservableField[Any, Any], Any]
    _observers_internal: dict[ObservableField[Any, Any], list[Observer]]
    _observers: dict[ObservableField[Any, Any], list[Observer]]

    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        # Initialize before subclass __init__, which may immediately assign fields
        # without calling super().__init__. Only field descriptors are shared.
        instance = super().__new__(cls)
        instance._observable_values = {}
        instance._observers_internal = {f: [] for f in cls._observable_fields.values()}
        instance._observers = {f: [] for f in cls._observable_fields.values()}
        return instance

    @property
    def F(self) -> type[Self]:  # pylint: disable=invalid-name
        """Convenience property to access the ObservableField types.
        For example in a method of the class MyClass(Observable), instead of
        `self.register_observer(MyClass.my_field, lambda x: print(x))`
        you can write `self.register_observer(self.F.my_field, lambda x: print(x))`.
        """
        return type(self)

    def set_val[T, I](self, of: ObservableField[T, I], val: I) -> None:
        """Write through a descriptor supplied explicitly by the caller."""
        # Descriptor dispatch is intentional; there is no equivalent set() method.
        of.__set__(self, val)  # pylint: disable=unnecessary-dunder-call

    def get_val[T, I](self, of: ObservableField[T, I]) -> T:
        """Read through a descriptor supplied explicitly by the caller."""
        return of.__get__(self)  # pylint: disable=unnecessary-dunder-call

    def _register_observer_internal(
        self, of: ObservableField[Any, Any], observer: Observer
    ) -> Observer:
        self._observers_internal[of].append(observer)
        return observer

    def _remove_observer_internal(
        self, of: ObservableField[Any, Any], observer: Observer
    ) -> None:
        self._observers_internal[of].remove(observer)

    def get_observers_internal(self, of: ObservableField[Any, Any]) -> list[Observer]:
        """Return a copy of the field's internal subscription list."""
        return copy(self._observers_internal[of])

    def register_observer(
        self, of: ObservableField[Any, Any], observer: Observer
    ) -> Observer:
        """Subscribe a callback to this instance's field and return the callback."""
        self._observers[of].append(observer)
        return observer

    def remove_observer(
        self, of: ObservableField[Any, Any], observer: Observer
    ) -> None:
        """Remove a previously registered callback from this instance's field."""
        self._observers[of].remove(observer)

    def get_observers(self, of: ObservableField[Any, Any]) -> list[Observer]:
        """Return a copy of the field's public subscription list."""
        return copy(self._observers[of])

    def notify(
        self,
        of_s: ObservableField[Any, Any] | list[ObservableField[Any, Any]],
        *a: Any,
        **kw: Any,
    ) -> None:
        """Notify internal and public subscribers of one or more fields."""
        if isinstance(of_s, ObservableField):
            of_s = [of_s]
        for of in of_s:
            for observer in self._observers_internal[of]:
                observer(*a, **kw)
            for observer in self._observers[of]:
                observer(*a, **kw)
