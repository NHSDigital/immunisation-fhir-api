"""Exceptions for the batch processor filter Lambda function"""


class InvalidBatchSizeError(Exception):
    """Raised when the SQS event batch size is anything other than 1"""

    pass


class EventAlreadyProcessingForSupplierAndVaccTypeError(Exception):
    """Raised when there is already a batch processing event in flight for the same supplier and vaccine type"""

    pass
