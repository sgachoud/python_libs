"""Exercise the public API in fresh interpreters, independent of import order."""

import importlib
from pathlib import Path
import subprocess
import sys

import pytest

import metacore


@pytest.mark.parametrize(
    "module_name",
    ["metacore", "metacore.constants", "metacore.annotations", "metacore.exceptions", "metacore.typing"],
)
def test_declared_public_exports(module_name):
    module = importlib.import_module(module_name)
    namespace = {}
    exec(f"from {module_name} import *", namespace)
    assert set(namespace) - {"__builtins__"} == set(module.__all__)
    assert all(namespace[name] is getattr(module, name) for name in module.__all__)


@pytest.mark.parametrize(
    "first_import",
    ["metacore", "metacore.constants", "metacore.annotations", "metacore.exceptions", "metacore.typing"],
)
def test_fresh_process_imports_and_registry_initialization(first_import, tmp_path):
    package_parent = str(Path(metacore.__file__).resolve().parent.parent)
    code = f"""
import sys
sys.path.insert(0, {package_parent!r})
import {first_import}
from metacore import (
    ConstantNamespace, TracedException, ValidationLevel, annotation_registry,
    convert_to_annotation, converter_from_annotation, default_from_annotation,
    defaulter_from_annotation, validate_from_annotation, validator_from_annotation,
)
from metacore import annotations
from metacore.exceptions import ConstantsModificationError

assert annotation_registry is annotations.annotation_registry
assert annotation_registry() is annotation_registry()
assert convert_to_annotation(list[int], ['1', '2']) == [1, 2]
assert converter_from_annotation(int)('3') == 3
assert default_from_annotation(tuple[int, str]) == (0, '')
assert defaulter_from_annotation(list[int])() == []
assert validate_from_annotation(list[int], [1]) == ValidationLevel.FULL
assert validator_from_annotation(list[int])(['1']) == ValidationLevel.PARTIAL

class Settings(ConstantNamespace):
    count: int = '42'
    values: list[int] = ['1', '2']

assert Settings.count == 42
assert Settings.values == [1, 2]
try:
    Settings.count = 0
except ConstantsModificationError as error:
    assert isinstance(error, TracedException)
else:
    raise AssertionError('Constants must remain immutable')

# Rebuilding the singleton must install handlers again without re-importing modules.
previous = annotation_registry()
annotation_registry.cache_clear()
assert annotation_registry() is not previous
assert convert_to_annotation(list[int], ['4']) == [4]
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], cwd=tmp_path,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_root_exports_share_feature_objects():
    from metacore import annotations, constants, exceptions

    assert metacore.ConstantNamespace is constants.ConstantNamespace
    assert metacore.TracedException is exceptions.TracedException
    assert metacore.ValidationLevel is annotations.ValidationLevel
    assert metacore.convert_to_annotation is annotations.convert_to_annotation
