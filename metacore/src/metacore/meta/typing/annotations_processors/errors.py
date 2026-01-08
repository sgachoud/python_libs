"""_summary_
"""

from ..errors import TypingError

class AnnotationProcessorError(TypingError):
    """Signals an error while creating a processor for an annotation."""


class DefaultingAnnotationError(TypingError):
    """Signals an error while attempting to get a default value for an annotation."""


class ConvertingToAnnotationTypeError(TypingError):
    """Signals an error while attempting to convert a value to an annotation type."""