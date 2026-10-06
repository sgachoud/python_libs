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
"""

from __future__ import annotations

from types import NotImplementedType
from typing import Any, Callable, Self, TYPE_CHECKING, get_args

from ..exceptions import AnnotationProcessorError, TypingError
from ..typing import Annotation
from ._types import (
    Converter, ConverterCreator, Defaulter, DefaulterCreator,
    Validator, ValidatorCreator,
)

if TYPE_CHECKING:
    from ._registry import AnnotationsRegistry

class AnnotationEntry:
    """Base class to hold all the processor, and processor creator for an annotation."""

    validate: Validator | None = None
    default: Defaulter | None = None
    convert: Converter | None = None

    def _prepare_inner_safe(
        self, annotation: Annotation, f: Callable[[Any], Any], p_name: str
    ) -> Any:
        try:
            return self.prepare_inner(annotation, f)
        except TypingError as e:
            raise AnnotationProcessorError(
                f"Could not create {p_name} for annotation '{annotation}'."
            ) from e

    def prepare_inner(self, annotation: Annotation, f: Callable[[Any], Any]) -> Any:
        """Can be overriden to change how the inner annotations are processed."""
        return list(map(f, get_args(annotation)))

    def raw_create_validator(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_validator to avoid creating inner validators.

        Args:
            annotation (Annotation): The annotation to create the validator for.
            registry (AnnotationsRegistry): The registry to use.

        Returns:
            Validator | NotImplementedType: The validator for the annotation, or NotImplemented.
        """
        return self.create_validator(
            self._prepare_inner_safe(
                annotation, registry.validator_from_annotation, "validator"
            ),
            annotation,
            registry,
        )

    def raw_create_defaulter(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_defaulter to avoid creating inner defaulters.

        Args:
            annotation (Annotation): The annotation to create the defaulter for.
            registry (AnnotationsRegistry): The registry to use.

        Returns:
            Defaulter | NotImplementedType: The defaulter for the annotation, or NotImplemented.
        """
        return self.create_defaulter(
            self._prepare_inner_safe(
                annotation, registry.defaulter_from_annotation, "defaulter"
            ),
            annotation,
            registry,
        )

    def raw_create_converter(
        self,
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        """Usually kept for private use. Can be overriden by sub-classes instead of
        create_converter to avoid creating inner converters.

        Args:
            annotation (Annotation): The annotation to create the converter for.
            registry (AnnotationsRegistry): The registry to use.

        Returns:
            Converter | NotImplementedType: The converter for the annotation, or NotImplemented.
        """
        return self.create_converter(
            self._prepare_inner_safe(
                annotation, registry.converter_from_annotation, "converter"
            ),
            annotation,
            registry,
        )

    def create_validator(
        self,
        inner_validators: list[Validator],
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Validator | NotImplementedType:
        """Create a validator for the annotation.

        Args:
            inner_validators (list[Validator]): The inner validators.
            annotation (Annotation): The complete annotation to create the validator for.

        Returns:
            Validator: The validator.
        """
        _ = inner_validators, annotation, registry
        return NotImplemented

    def create_defaulter(
        self,
        inner_defaulter: list[Defaulter],
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Defaulter | NotImplementedType:
        """Create a defaulter for the annotation.

        Args:
            inner_defaulter (list[Defaulter]): The inner defaulters.
            annotation (Annotation): The complete annotation to create the defaulter for.

        Returns:
            Defaulter: The defaulter.
        """
        _ = inner_defaulter, annotation, registry
        return NotImplemented

    def create_converter(
        self,
        inner_converters: list[Converter],
        annotation: Annotation,
        registry: AnnotationsRegistry,
        /,
    ) -> Converter | NotImplementedType:
        """Create a converter for the annotation.

        Args:
            inner_converters (list[Converter]): The inner converters.
            annotation (Annotation): The complete annotation to create the converter for.

        Returns:
            Converter: The converter.
        """
        _ = inner_converters, annotation, registry
        return NotImplemented


class HousingAnnotationEntry(AnnotationEntry):
    """House annotation processors given as independent callables."""

    def __init__(
        self,
        validator: Validator | None = None,
        defaulter: Defaulter | None = None,
        converter: Converter | None = None,
        validator_creator: ValidatorCreator | None = None,
        defaulter_creator: DefaulterCreator | None = None,
        converter_creator: ConverterCreator | None = None,
    ):
        self.validate = validator or self.validate
        self.default = defaulter or self.default
        self.convert = converter or self.convert
        self.create_validator = validator_creator or self.create_validator
        self.create_defaulter = defaulter_creator or self.create_defaulter
        self.create_converter = converter_creator or self.create_converter

    def _use_direct_processor(
        self, _annotation: Annotation, _registry: AnnotationsRegistry, /
    ) -> NotImplementedType:
        """A directly replaced operation supersedes its previous creator."""
        return NotImplemented

    def set_validator(self, validator: Validator) -> Self:
        """Set the validator for the annotation processor.
           Can be used as a decorator.

        Args:
            validator (Validator): The validator to set.

        Returns:
            Self: The annotation processor.
        """
        self.validate = validator
        self.raw_create_validator = self._use_direct_processor
        return self

    def set_defaulter(self, defaulter: Defaulter) -> Self:
        """Set the defaulter for the annotation processor.
           Can be used as a decorator.

        Args:
            defaulter (Defaulter): The defaulter to set.

        Returns:
            Self: The annotation processor.
        """
        self.default = defaulter
        self.raw_create_defaulter = self._use_direct_processor
        return self

    def set_converter(self, converter: Converter) -> Self:
        """Set the converter for the annotation processor.
           Can be used as a decorator.

        Args:
            converter (Converter): The converter to set.

        Returns:
            Self: The annotation processor.
        """
        self.convert = converter
        self.raw_create_converter = self._use_direct_processor
        return self

    def set_validator_creator(self, validator_creator: ValidatorCreator) -> Self:
        """Set the validator creator for the annotation processor.
           Can be used as a decorator.

        Args:
            validator_creator (ValidatorCreator): The validator creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_validator = validator_creator
        self.raw_create_validator = super().raw_create_validator
        return self

    def set_defaulter_creator(self, defaulter_creator: DefaulterCreator) -> Self:
        """Set the defaulter creator for the annotation processor.
           Can be used as a decorator.

        Args:
            defaulter_creator (DefaulterCreator): The defaulter creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_defaulter = defaulter_creator
        self.raw_create_defaulter = super().raw_create_defaulter
        return self

    def set_converter_creator(self, converter_creator: ConverterCreator) -> Self:
        """Set the converter creator for the annotation processor.
           Can be used as a decorator.

        Args:
            converter_creator (ConverterCreator): The converter creator to set.

        Returns:
            Self: The annotation processor.
        """
        self.create_converter = converter_creator
        self.raw_create_converter = super().raw_create_converter
        return self

    @classmethod
    def from_processor(cls, processor: AnnotationEntry | None) -> Self:
        """Create a HousingAnnotationProcessor from an AnnotationProcessor."""
        if not processor:
            return cls()
        entry = cls(
            validator=processor.validate,
            defaulter=processor.default,
            converter=processor.convert,
            validator_creator=processor.create_validator,
            defaulter_creator=processor.create_defaulter,
            converter_creator=processor.create_converter,
        )
        entry.prepare_inner = processor.prepare_inner
        entry.raw_create_validator = processor.raw_create_validator
        entry.raw_create_defaulter = processor.raw_create_defaulter
        entry.raw_create_converter = processor.raw_create_converter
        return entry
