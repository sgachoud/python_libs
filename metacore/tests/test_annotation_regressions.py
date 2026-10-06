"""Regression coverage for annotation processing and registry customization."""

from collections.abc import Sequence
from typing import Annotated, Literal

import pytest

from metacore import ConstantNamespace, fully_matches_annotation
from metacore.annotations import AnnotationEntry, AnnotationsRegistry, ValidationLevel
from metacore.exceptions import (
    AnnotationProcessorError, ConstantsModificationError, ConvertingToAnnotationTypeError,
    DefaultingAnnotationError,
)
from metacore.typing import resolve_annotation_types

type IntegerItems = list[int]
type Items[T] = list[T]
type Pair[T, U] = tuple[T, U]
type Marked[T] = Annotated[list[T], "marked"]
type NestedAlias[T] = Items[tuple[T, str]]
type OptionalAlias[T] = T | None
type ForwardAlias = list["ForwardItem"]
type Tree = int | list[Tree]
type RecursiveList = list[RecursiveList]
type DirectCycle = DirectCycle
type LeftCycle = list[RightCycle]
type RightCycle = dict[str, LeftCycle]
type GrowingCycle[T] = list[GrowingCycle[list[T]]]
type QuotedCycle = list["QuotedCycle"]


class ForwardItem:
    def __init__(self, value=0):
        self.value = int(value)


def test_constants_cannot_be_deleted():
    class Settings(ConstantNamespace):
        value: int = 1

    with pytest.raises(ConstantsModificationError):
        del Settings.value
    with pytest.raises(ConstantsModificationError):
        del Settings.__constants__
    assert Settings.items() == [("value", 1)]


@pytest.mark.parametrize("annotation", [Sequence[int], frozenset[int]])
@pytest.mark.parametrize(
    "operation",
    ["validator_from_annotation", "converter_from_annotation", "defaulter_from_annotation"],
)
def test_unhandled_generics_do_not_discard_type_arguments(annotation, operation):
    with pytest.raises(AnnotationProcessorError, match="type arguments"):
        getattr(AnnotationsRegistry(), operation)(annotation)


def test_overriding_literal_converter_preserves_literal_validation():
    registry = AnnotationsRegistry()
    registry.register_converter(Literal, lambda value: value)
    assert registry.validate_with_annotation(Literal["a", "b"], "a")
    assert not registry.validate_with_annotation(Literal["a", "b"], "c")
    assert registry.default_annotation(Literal["a", "b"]) == "a"
    assert registry.convert_to_annotation(Literal["a", "b"], "custom") == "custom"


def test_overriding_one_operation_preserves_custom_raw_creators():
    class CustomEntry(AnnotationEntry):
        def raw_create_validator(self, annotation, registry, /):
            return lambda value: value == "accepted"

    registry = AnnotationsRegistry()
    registry.register_processor(list, CustomEntry())
    registry.register_converter(list, lambda value: value)
    assert registry.validate_with_annotation(list[int], "accepted")
    assert not registry.validate_with_annotation(list[int], "rejected")
    registry.register_validator_creator(list, lambda *_args: lambda value: value == "new")
    assert registry.validate_with_annotation(list[int], "new")
    assert not registry.validate_with_annotation(list[int], "accepted")


@pytest.mark.parametrize("container", [list, set, dict])
def test_empty_container_defaults_do_not_need_element_defaults(container):
    class NoDefault:
        def __init__(self, argument):
            self.argument = argument

    annotation = container[str, NoDefault] if container is dict else container[NoDefault]
    registry = AnnotationsRegistry()
    factory = registry.defaulter_from_annotation(annotation)
    assert factory() == container()
    assert factory() is not factory()


def test_variadic_tuple_validation_and_conversion():
    registry = AnnotationsRegistry()
    validator = registry.validator_from_annotation(tuple[int, ...])
    assert validator(()) == ValidationLevel.FULL
    assert validator((1, 2, 3)) == ValidationLevel.FULL
    assert validator((1, "2")) == ValidationLevel.PARTIAL
    assert validator([1, 2]) == ValidationLevel.NONE
    converter = registry.converter_from_annotation(tuple[int, ...])
    original = (1, 2)
    assert converter(original) is original
    assert converter(iter(["1", "2", "3"])) == (1, 2, 3)
    assert converter([]) == ()
    with pytest.raises(ConvertingToAnnotationTypeError):
        converter(["invalid"])
    with pytest.raises(ConvertingToAnnotationTypeError):
        converter(1)


def test_fixed_and_empty_tuple_constraints_remain_enforced():
    registry = AnnotationsRegistry()
    assert registry.convert_to_annotation(tuple[int, str], ["1", 2]) == (1, "2")
    assert registry.convert_to_annotation(tuple[()], []) == ()
    assert registry.validate_with_annotation(tuple[()], ()) == ValidationLevel.FULL
    assert registry.validate_with_annotation(tuple[()], (1,)) == ValidationLevel.NONE
    with pytest.raises(ConvertingToAnnotationTypeError):
        registry.convert_to_annotation(tuple[int, str], [1])


def test_default_factory_defers_side_effects_and_reports_causes():
    calls = []

    class Item:
        def __init__(self):
            calls.append(self)

    registry = AnnotationsRegistry()
    factory = registry.defaulter_from_annotation(Item)
    assert calls == []
    first = factory()
    second = factory()
    assert calls == [first, second]
    assert first is not second

    class Broken:
        def __init__(self):
            raise ValueError("construction failed")

    factory = registry.defaulter_from_annotation(Broken)
    with pytest.raises(DefaultingAnnotationError) as caught:
        factory()
    assert isinstance(caught.value.__cause__, ValueError)


def test_variadic_tuple_default_does_not_create_element_factories():
    registry = AnnotationsRegistry()
    assert registry.default_annotation(tuple[Sequence[int], ...]) == ()


def test_annotated_metadata_is_preserved_and_exact_handlers_take_precedence():
    annotation = Annotated[int, "special"]
    registry = AnnotationsRegistry()
    assert resolve_annotation_types({"x": annotation})["x"] == annotation
    assert registry.convert_to_annotation(annotation, "2") == 2
    assert registry.default_annotation(annotation) == 0
    assert registry.validate_with_annotation(annotation, 2)
    registry.register_converter(annotation, lambda _value: 99)
    registry.register_defaulter(annotation, lambda: 42)
    registry.register_validator(annotation, lambda value: value == 99)
    assert registry.convert_to_annotation(list[annotation], ["2"]) == [99]
    assert registry.default_annotation(annotation) == 42
    assert not registry.validate_with_annotation(annotation, 2)
    assert registry.validate_with_annotation(annotation, 99)
    assert registry.convert_to_annotation(int, "2") == 2


def test_annotated_forward_references_and_unhashable_metadata():
    registry = AnnotationsRegistry()
    annotation = Annotated["Item", {"description": "unhashable metadata"}]
    assert registry.convert_to_annotation(annotation, "2", nlocals={"Item": int}) == 2


def test_processors_are_cached_and_registration_invalidates_composites():
    registry = AnnotationsRegistry()
    original = registry.converter_from_annotation(list[int])
    assert registry.converter_from_annotation(list[int]) is original
    registry.register_converter(int, lambda _value: 99)
    replacement = registry.converter_from_annotation(list[int])
    assert replacement is not original
    assert replacement(["1"]) == [99]
    assert original(["1"]) == [1]

    for operation in ("validator_from_annotation", "defaulter_from_annotation"):
        factory = getattr(registry, operation)
        assert factory(tuple[int, str]) is factory(tuple[int, str])


def test_cache_preserves_union_order_including_nested_unions():
    registry = AnnotationsRegistry()
    assert registry.default_annotation(int | str) == 0
    assert registry.default_annotation(str | int) == ""
    assert registry.default_annotation(tuple[int | str]) == (0,)
    assert registry.default_annotation(tuple[str | int]) == ("",)
    assert registry.convert_to_annotation(int | str, 1.5) == 1
    assert registry.convert_to_annotation(str | int, 1.5) == "1.5"


def test_failed_processor_creation_is_not_cached():
    registry = AnnotationsRegistry()
    calls = []

    def create(*_args):
        calls.append(1)
        if len(calls) == 1:
            raise AnnotationProcessorError("retry")
        return lambda value: value

    registry.register_converter_creator(list, create)
    with pytest.raises(AnnotationProcessorError):
        registry.converter_from_annotation(list[int])
    converter = registry.converter_from_annotation(list[int])
    assert registry.converter_from_annotation(list[int]) is converter
    assert len(calls) == 2


@pytest.mark.parametrize(
    "method",
    [
        "clear_validator_cache_for_annotation",
        "clear_defaulter_cache_for_annotation",
        "clear_converter_cache_for_annotation",
        "clear_cache_for_annotation",
    ],
)
def test_explicit_cache_clearing_invalidates_parent_processors(method):
    registry = AnnotationsRegistry()
    converter = registry.converter_from_annotation(list[int])
    validator = registry.validator_from_annotation(list[int])
    defaulter = registry.defaulter_from_annotation(tuple[int])
    getattr(registry, method)("Item", nlocals={"Item": int})
    assert registry.converter_from_annotation(list[int]) is not converter
    assert registry.validator_from_annotation(list[int]) is not validator
    assert registry.defaulter_from_annotation(tuple[int]) is not defaulter


def test_plain_and_generic_type_aliases():
    registry = AnnotationsRegistry()
    assert registry.convert_to_annotation(IntegerItems, ["1"]) == [1]
    assert registry.convert_to_annotation(Items[int], ["1"]) == [1]
    assert registry.convert_to_annotation(Pair[int, str], ["1", 2]) == (1, "2")
    assert registry.convert_to_annotation(Marked[int], ["1"]) == [1]
    assert registry.convert_to_annotation(NestedAlias[int], [["1", 2]]) == [(1, "2")]
    assert registry.convert_to_annotation(OptionalAlias[int], "1") == 1
    assert registry.default_annotation(OptionalAlias[int]) is None
    assert registry.default_annotation(Items[int]) == []
    assert registry.validate_with_annotation(IntegerItems, [1]) == ValidationLevel.FULL
    assert registry.validate_with_annotation(Items[int], ["1"]) == ValidationLevel.PARTIAL
    assert registry.convert_to_annotation(ForwardAlias, ["1"])[0].value == 1


def test_alias_specific_processors_take_precedence():
    registry = AnnotationsRegistry()
    registry.register_converter(Items[int], lambda _value: [99])
    assert registry.convert_to_annotation(Items[int], ["1"]) == [99]
    assert registry.convert_to_annotation(Items[str], [1]) == ["1"]


@pytest.mark.parametrize("annotation", [Items, Pair[int], Items[int, str]])
def test_generic_aliases_require_the_declared_number_of_type_arguments(annotation):
    registry = AnnotationsRegistry()
    with pytest.raises(AnnotationProcessorError, match="type arguments"):
        registry.converter_from_annotation(annotation)


@pytest.mark.parametrize(
    "annotation",
    [Tree, RecursiveList, DirectCycle, LeftCycle, GrowingCycle[int], QuotedCycle, list[Tree]],
)
@pytest.mark.parametrize(
    "operation",
    ["validator_from_annotation", "converter_from_annotation", "defaulter_from_annotation"],
)
def test_recursive_aliases_are_rejected_consistently(annotation, operation):
    registry = AnnotationsRegistry()
    for _ in range(2):
        with pytest.raises(AnnotationProcessorError, match="Recursive type aliases"):
            getattr(registry, operation)(annotation)
    assert registry.convert_to_annotation(Items[int], ["1"]) == [1]


def test_finite_nested_aliases_and_metadata_are_not_recursive():
    registry = AnnotationsRegistry()
    assert registry.convert_to_annotation(Items[Items[int]], [["1"]]) == [[1]]
    assert registry.convert_to_annotation(Annotated[int, Tree], "1") == 1


@pytest.mark.parametrize("api", [fully_matches_annotation, AnnotationsRegistry().fully_matches_annotation])
def test_full_match_is_boolean_and_forwards_resolution_namespaces(api):
    assert api(int, 1) is True
    assert api(int, "1") is False
    assert api(list[int], [1]) is True
    assert api(list[int], ["1"]) is False
    assert api(list[int], (1,)) is False
    assert api("list[Item]", [1], nglobals={"Item": str}, nlocals={"Item": int}) is True
    with pytest.raises(AnnotationProcessorError):
        api(Sequence[int], [1])


@pytest.mark.parametrize(
    "result, expected",
    [(True, True), (False, False), (ValidationLevel.FULL, True),
     (ValidationLevel.PARTIAL, False), (ValidationLevel.NONE, False)],
)
def test_full_match_handles_custom_validation_results(result, expected):
    registry = AnnotationsRegistry()
    registry.register_validator(int, lambda _value: result)
    assert registry.fully_matches_annotation(int, 1) is expected


def test_existing_partial_truthiness_and_literal_fallback_are_preserved():
    registry = AnnotationsRegistry()
    result = registry.validate_with_annotation(list[int], ["1"])
    assert result == ValidationLevel.PARTIAL
    assert bool(result) is True
    assert registry.convert_to_annotation(Literal["a", "b"], "unknown") == "a"
    assert registry.validate_with_annotation(Literal[1], True) == ValidationLevel.FULL
    assert registry.convert_to_annotation(Literal[1], True) is True
