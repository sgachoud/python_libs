"""
Author: Sébastien Gachoud
Created: 2025-07-11
Description: Tests for the constants module.
🦙
"""

__author__ = "Sébastien Gachoud"
__version__ = "1.0.0"
__license__ = "MIT"

import pytest
from sg_lib.src.sg_lib.meta.classes.constants import (
    ConstantNamespace,
    ConstantsInstantiationError,
    ConstantsCompositionError,
    ConstantsModificationError,
)


def test_instantiation_raises_error():
    """Test"""

    class MyConstants(ConstantNamespace):
        """Test"""

        A: int = 1

    with pytest.raises(ConstantsInstantiationError):
        _ = MyConstants()


def test_missing_annotation_value_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int

        _ = BadConstants.A


def test_non_true_type_annotation_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int | str = 1

        _ = BadConstants.A


def test_adding_init_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int = 1

            def __init__(self):
                pass

        _ = BadConstants.A


def test_adding_new_raises_composition_error():
    """Test"""
    with pytest.raises(ConstantsCompositionError):

        class BadConstants(ConstantNamespace):
            """Test"""

            A: int = 1

            def __new__(cls):
                pass

        _ = BadConstants.A


def test_modifying_constant_raises_modification_error():
    """Test"""

    class MyConstants(ConstantNamespace):
        """Test"""

        A: int = 1

    with pytest.raises(ConstantsModificationError):
        MyConstants.A = 2


def test_valid_constant_class_creation():
    """Test"""

    class GoodConstants(ConstantNamespace):
        """Test"""

        A: int = 1
        B: str = "hello"

    assert GoodConstants.A == 1
    assert GoodConstants.B == "hello"
