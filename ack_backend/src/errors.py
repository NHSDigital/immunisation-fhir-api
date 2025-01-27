"""Custom exceptions for the Filename Processor."""


class DuplicateFileError(Exception):
    """A custom exception for when it is identified that the file is a duplicate."""


class ProcessingError(Exception):
    """A custom exception for when it is identified that supplier_vaccine file is under processing"""


class UnhandledAuditTableError(Exception):
    """A custom exception for when an unexpected error occurs whilst adding the file to the audit table."""


class VaccineTypePermissionsError(Exception):
    """A custom exception for when the supplier does not have the necessary vaccine type permissions."""


class InvalidFileKeyError(Exception):
    """A custom exception for when the file key is invalid."""


class InvalidSupplierError(Exception):
    """A custom exception for when the supplier has not been correctly identified."""


class UnhandledSqsError(Exception):
    """A custom exception for when an unexpected error occurs whilst sending a message to SQS."""
