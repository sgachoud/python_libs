"""Exercise default annotation behavior without the future annotations import."""

from decimal import Decimal
from pathlib import Path

import pytest

from observable.observable import Auto, Observable, ObservableField, auto_field


def test_default_annotations_resolve_global_and_class_local_types():
    class Model(Observable):
        Scalar = Decimal
        value: ObservableField[Scalar, str] = auto_field(default=Auto)
        directory: ObservableField[Path, str] = auto_field(default=Auto)

    instance = Model()
    assert instance.value == Decimal(0)
    events = []
    instance.register_observer(Model.value, events.append)
    instance.value = "1.25"
    instance.directory = "documents"
    assert instance.value == Decimal("1.25")
    assert instance.directory == Path("documents")
    assert events == ["1.25"]


def test_default_annotations_support_quoted_fields_and_inheritance():
    class Parent(Observable):
        value: "ObservableField[int, str]" = auto_field(default=0)

    class Child(Parent):
        other: ObservableField[int, str] = auto_field(default=1)

    first, second = Child(), Child()
    first.value = "2"
    first.other = "3"
    assert (first.value, first.other) == (2, 3)
    assert (second.value, second.other) == (0, 1)


def test_missing_annotations_still_fail_with_a_clear_error():
    with pytest.raises(TypeError, match="must have a type annotation"):

        class Missing(Observable):
            value = auto_field(default=0)
