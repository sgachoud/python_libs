"""Regression coverage for typed descriptors and observable instance behavior."""

from __future__ import annotations

from typing import assert_type
from pathlib import Path

import pytest

from metacore.annotations import AnnotationsRegistry
from observable.observable import (
    Access,
    Auto,
    Observable,
    ObservableField,
    ReadAccessViolationError,
    UninitializedError,
    WriteAccessViolationError,
    auto_field,
)


class Counter(Observable):
    value: ObservableField[int, str] = auto_field(default=0)


def test_field_annotations_resolve_module_and_class_local_names():
    class Scoped(Observable):
        from decimal import Decimal as Scalar

        value: ObservableField[Scalar, str] = auto_field(default=Auto)
        directory: ObservableField[Path, str] = auto_field(default=Auto)

    instance = Scoped()
    instance.value = "1.25"
    instance.directory = "documents"
    assert instance.value == Scoped.Scalar("1.25")
    assert instance.directory == Path("documents")


def test_conversion_notifications_and_instance_isolation():
    first, second = Counter(), Counter()
    events: list[str] = []
    first.register_observer(Counter.value, events.append)

    first.value = "42"
    first.value = "42"

    assert first.value == 42
    assert second.value == 0
    assert events == ["42"]
    assert second.get_observers(Counter.value) == []


def test_explicit_descriptor_access_preserves_types():
    counter = Counter()
    counter.set_val(Counter.value, "3")
    assert counter.get_val(Counter.value) == 3
    assert_type(counter.get_val(Counter.value), int)
    assert_type(Counter.value, ObservableField[int, str])


def test_inherited_fields_are_not_initialized_twice():
    class Child(Counter):
        other: ObservableField[int, str] = auto_field(default=1)

    first, second = Child(), Child()
    first.value = "7"
    first.other = "8"
    assert first.value == 7
    assert first.other == 8
    assert second.value == 0
    assert second.other == 1


def test_subclass_can_assign_fields_in_its_initializer():
    class Initialized(Counter):
        def __init__(self, value: str):
            self.value = value

    assert Initialized("5").value == 5


def test_converter_decorator():
    class Decorated(Observable):
        value: ObservableField[int, str] = auto_field(default=0)

        @staticmethod
        @value.converter
        def parse(value: str) -> int:
            return int(value) + 10

    instance = Decorated()
    instance.value = "2"
    assert instance.value == 12


def test_custom_registry_and_automatic_default():
    registry = AnnotationsRegistry()
    registry.register_converter(int, lambda value: int(value) + 10)

    class Custom(Observable):
        values = ObservableField[list[int], list[str]](
            default=Auto, custom_annotation_registry=registry
        )

    instance = Custom()
    assert instance.values == []
    instance.values = ["1", "2"]
    assert instance.values == [11, 12]


def test_read_and_write_access_policies():
    class Restricted(Observable):
        read_only = ObservableField[int](default=1, access=Access.read)
        write_only = ObservableField[int](access=Access.write)

    instance = Restricted()
    assert instance.read_only == 1
    with pytest.raises(WriteAccessViolationError):
        instance.read_only = 2
    instance.write_only = 3
    with pytest.raises(ReadAccessViolationError):
        _ = instance.write_only


def test_uninitialized_field():
    class Pending(Observable):
        value = ObservableField[int]()

    with pytest.raises(UninitializedError):
        _ = Pending().value


def test_observer_removal_and_copied_subscriptions():
    counter = Counter()
    events: list[str] = []
    observer = counter.register_observer(Counter.value, events.append)
    counter.get_observers(Counter.value).clear()
    counter.value = "1"
    counter.remove_observer(Counter.value, observer)
    counter.value = "2"
    assert events == ["1"]
