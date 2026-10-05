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
import numpy as np
from enum import IntFlag
from enum import auto as e_auto
from typing import (Any, Callable, Self, TypeVar, overload,
                    get_args, get_origin, get_type_hints, cast)
from dataclasses import dataclass
from metacore.abstract.exceptions.traced_exceptions import TracedException
from metacore.meta.typing_utilities.annotations_processors.processors import AnnotationsRegistery, annotation_registry, default_from_annotation

# TODO: replace with metacore.meta.typing_utilities ones
def resolve_annotation_types(annotations: dict[str, Any], nglobals: dict[str, Any] | None = None,
                              nlocals: dict[str, Any] | None = None) -> dict[str, Any]:
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
    return get_type_hints(X, nglobals, nlocals)

class ObservableFieldError(TracedException): ...
class UninitializedError(ObservableFieldError): ...
class MemberDefinitionError(ObservableFieldError): ...
class TypeFormatError(ObservableFieldError): ...
class DefaultValueError(ObservableFieldError): ...
class AccessViolationError(ObservableFieldError): ...
class ReadAccessViolationError(AccessViolationError): ...
class WriteAccessViolationError(AccessViolationError): ...
class PropertyDefinitionError(ObservableFieldError): ...
class GetterDefinitionError(ObservableFieldError): ...
class SetterDefinitionError(ObservableFieldError): ...

class Access(IntFlag):
  """Access policy of an observable field.
  
  Attributes:
      none (int): No access. The field cannot be written or read. This can be
        useful to have a notification only field. All fields can be observed.
      read (int): Read access. Allows the field to be read.
      write (int): Write access. Allows the field to be written.
  """
  none = 0
  read = e_auto()
  write = e_auto()
  both = read | write
  r = read
  w = write
  rw = read | write

class Empty:
  """Represent a value not provided.
  """
  def __new__(cls) -> type:
    return Empty

  def __repr__(self) -> str:
    return "Observably Empty"

  def __bool__(self) -> bool:
    return False


class Auto:
  """Request the default to be automatically derived from the field's type annotation.
  """
  def __new__(cls) -> type:
    return Auto

  def __repr__(self) -> str:
    return "Observably Auto"


class ObservableFieldDecorators[T, I]:

  def converter(self, converter: Callable[[I], T]) -> Callable[[I], T]:
    self.convert = converter
    return converter

  def comparator(self, comparator: Callable[[T, T], bool]) -> Callable[[T, T], bool]:
    self.compare = comparator
    return comparator

  def assigner[S: Observable](self, assigner: Callable[[S, T], None]) -> Callable[[S, T], None]:
    self.assign = cast(Callable[[Observable, T], None], assigner)
    return assigner

  def setter[S: Observable](self, setter: Callable[[S, I], None]) -> Callable[[S, I], None]:
    self.set = cast(Callable[[Observable, I], None], setter)
    return setter

  def getter[S: Observable](self, getter: Callable[[S], T]) -> Callable[[S], T]:
    self.get = cast(Callable[[Observable], T], getter)
    return getter


@dataclass
class AutoField[T, I = T](ObservableFieldDecorators[T, I]):
  default: T | type[Empty] | type[Auto] = Empty
  default_factory: Callable[[], T] | None = None
  access: Access=Access.both
  custom_annotation_registry: AnnotationsRegistery | None = None
  force_type: tuple[Any, Any] | Empty = Empty()
  convert: Callable[[I], T] | None = None
  compare: Callable[[T, T], bool] | None = None
  assign: Callable[[Observable, T], None] | None = None
  set: Callable[[Observable, I], None] | None = None
  get: Callable[[Observable], T] | None = None

  def as_observable_field(self) -> ObservableField:
    return ObservableField(
      default=self.default,
      default_factory=self.default_factory,
      access=self.access,
      custom_annotation_registry=self.custom_annotation_registry,
      force_type=self.force_type,
      converter=self.convert,
      comparator=self.compare,
      assigner=self.assign,
      setter=self.set,
      getter=self.get
    )

def auto_field[T, I = T](
    default: T | type[Empty] | type[Auto] = Empty,
    default_factory: Callable[[], T] | None = None,
    access: Access=Access.both,
    custom_annotation_registry: AnnotationsRegistery | None = None,
    force_type: tuple[Any, Any] | Empty = Empty(),
    converter: Callable[[I], T] | None = None,
    comparator: Callable[[T, T], bool] | None = None,
    assigner: Callable[[Observable, T], None] | None = None,
    setter: Callable[[Observable, I], None] | None = None,
    getter: Callable[[Observable], T] | None = None) -> Any:
  return AutoField(default, default_factory, access, custom_annotation_registry,
                   force_type, converter, comparator, assigner, setter, getter)

class ObservableField[T, I = T](ObservableFieldDecorators[T, I]):
  def __init__(self,
              default: T | type[Empty] | type[Auto] = Empty,
              default_factory: Callable[[], T] | None = None,
              access: Access=Access.both,
              custom_annotation_registry: AnnotationsRegistery | None = None,
              force_type: tuple[Any, Any] | Empty = Empty(),
              converter: Callable[[I], T] | None = None,
              comparator: Callable[[T, T], bool] | None = None,
              assigner: Callable[[Observable, T], None] | None = None,
              setter: Callable[[Observable, I], None] | None = None,
              getter: Callable[[Observable], T] | None = None) -> None:

    if default is not Empty and default_factory is not None:
      raise ValueError("default_value and default_factory can not be provided at the same time.")

    self.__post_value = [default, force_type, converter, comparator, assigner, setter, getter]


    self.default_factory = default_factory
    self._registry = custom_annotation_registry or annotation_registry()
    self.access = access

    self.name = "Undefined"

  def __post_init__(self):
    (default_value, force_type, converter, comparator,
     assigner, setter, getter) = self.__post_value
    del self.__post_value
    if isinstance(force_type, tuple):
      _type, input_types = force_type
    elif (orig_class:=getattr(self, "__orig_class__", None)) is not None:
      _type, input_types = get_args(orig_class)
      if isinstance(input_types, TypeVar):
        input_types = _type
    else:
      raise ValueError(
        "ObservableField must be used with an Observable class. If you think it is done properly"
        "but still fails, please open an issue on github. To bypass this error, you can provide "
        "the type and input types manually through force_type.")
    self.default = self.__make_default(default_value, self.default_factory, _type)
    self.type = _type
    self.input_types = input_types

    self.default_convert: Callable[[I], T] = self._registry.converter_from_annotation(_type)
    self._converter: Callable[[I], T] = converter or self.default_convert
    self._comparator: Callable[[Any, Any], bool] = comparator or self.default_compare
    self._assigner = assigner or self.default_assign
    self._setter = setter or self.default_set
    self._getter = getter or self.default_get

  def __make_default(self, default, factory, _type):
    if default is Auto:
      return self._registry.default_annotation(_type)
    if default is not Empty:
      return default
    if factory is not None:
      return factory()
    return Empty

  def default_compare(self, value1: Any, value2: Any) -> bool:
    if isinstance(value1, np.ndarray) or isinstance(value2, np.ndarray):
      return np.array_equal(value1, value2)
    return value1 == value2

  def default_assign(self, instance: Observable, value: T) -> None:
    instance._observable_values[self] = value

  def default_set(self, instance: Observable, value: I) -> None:
    new_value = self._converter(value)
    if self in instance._observable_values and self._comparator(instance._observable_values[self], new_value):
      return
    self._assigner(instance, new_value)
    instance.notify(self, value)

  def default_get(self, instance: Observable) -> T:
    if Access.read not in self.access:
      raise ReadAccessViolationError(f"Cannot read attribute '{self.name}', read is not allowed.")
    if Access.write not in self.access:
      if self.default is not Empty:
        return cast(T, self.default)
      else:
        raise UninitializedError(f"Attribute '{self.name}' has not value and is not writable.")
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
  def __get__(self, instance: Observable, owner: type[Observable] | None = None, /) -> T: ...

  def __get__(self, instance: Observable | None, owner: type[Observable] | None = None) -> T | Self:
    if instance is None:
      return self
    return self._getter(instance)

  def __set__(self, instance: Observable, value: I) -> None:
    if Access.write not in self.access:
      raise WriteAccessViolationError(f"Cannot write attribute '{self.name}', write is not allowed.")
    self._setter(instance, value)


class ObservableMeta(type):
  def __new__(mcs, name, bases, namespace, /, **kwargs):
    fields = mcs._collect_observable_fields(bases, namespace)
    for field in fields.values():
      field.__post_init__()
    mcs._populate_observables(namespace, fields)
    return super().__new__(mcs, name, bases, namespace, **kwargs)

  @classmethod
  def _collect_observable_fields(mcs, bases, namespace):
    fields = {}
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
  def _process_auto_field(mcs, namespace, name: str, field: AutoField) -> ObservableField:
    annotation = namespace.get("__annotations__", {}).get(name, None)
    if annotation is None:
      raise TypeError(f"Automatic field '{name}' must have a type annotation.")
    module = sys.modules.get(namespace.get("__module__"))
    nglobals = module.__dict__ if module is not None else None
    annotation = resolve_annotation_types({name: annotation}, nglobals, namespace)[name]
    orig = get_origin(annotation)
    if orig is None or orig is not ObservableField:
      raise TypeError(f"Automatic field '{name}' must be annotated as an ObservableField.")
    of = field.as_observable_field()
    setattr(of, "__orig_class__", annotation)
    return of


  @classmethod
  def _populate_observables(mcs, namespace, fields: dict[str, ObservableField]):
    namespace["_observable_fields"] = fields


class Observable(metaclass=ObservableMeta):

  _observable_fields: dict[str, ObservableField]
  _observable_values: dict[ObservableField, Any]
  _observers_internal: dict[ObservableField, list[Callable[[Any], Any]]]
  _observers: dict[ObservableField, list[Callable[[Any], Any]]]

  def __new__(cls, *args, **kwargs):
    # Initialize before subclass __init__, which may immediately assign fields
    # without calling super().__init__. Only field descriptors are shared.
    instance = super().__new__(cls)
    instance._observable_values = {}
    instance._observers_internal = {f: [] for f in cls._observable_fields.values()}
    instance._observers = {f: [] for f in cls._observable_fields.values()}
    return instance

  @property
  def F(self) -> type[Self]:
    """Convenience property to access the ObservableField types.
      For example in a method of the class MyClass(Observable), instead of
      `self.register_observer(MyClass.my_field, lambda x: print(x))`
      you can write `self.register_observer(self.F.my_field, lambda x: print(x))`.
    """
    return type(self)

  def set_val(self, of: ObservableField, val: Any):
    of.__set__(self, val)

  def get_val(self, of: ObservableField):
    return of.__get__(self)

  def _register_observer_internal(self, of: ObservableField, observer: Callable) -> Callable:
    self._observers_internal[of].append(observer)
    return observer

  def _remove_observer_internal(self, of: ObservableField, observer: Callable):
    self._observers_internal[of].remove(observer)

  def get_observers_internal(self, of: ObservableField):
    return copy(self._observers_internal[of])

  def register_observer(self, of: ObservableField, observer: Callable) -> Callable:
    self._observers[of].append(observer)
    return observer

  def remove_observer(self, of: ObservableField, observer: Callable):
    self._observers[of].remove(observer)

  def get_observers(self, of: ObservableField):
    return copy(self._observers[of])

  def notify(self, of_s: ObservableField | list[ObservableField], *a, **kw):
    if isinstance(of_s, ObservableField):
      of_s = [of_s]
    for of in of_s:
      for observer in self._observers_internal[of]:
        observer(*a, **kw)
      for observer in self._observers[of]:
        observer(*a, **kw)
