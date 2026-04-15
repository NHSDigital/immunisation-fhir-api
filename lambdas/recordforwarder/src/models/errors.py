from dataclasses import dataclass


@dataclass
class MessageNotSuccessfulError(Exception):
    """
    Generic error message for any scenario which either prevents sending to the Imms API, or which results in a
    non-successful response from the Imms API
    """

    def __init__(self, message=None):
        self.message = message


@dataclass
class RecordProcessorError(Exception):
    """
    Exception for re-raising exceptions which have already occurred in the Record Processor.
    The diagnostics dictionary received from the Record Processor is passed to the exception as an argument
    and is stored as an attribute.
    """

    def __init__(self, diagnostics_dictionary: dict):
        self.diagnostics_dictionary = diagnostics_dictionary
