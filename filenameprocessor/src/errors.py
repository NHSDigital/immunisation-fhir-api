"""Custom exceptions for the Filename Processor."""


class UnhandledAuditTableError(Exception):
    """A custom exception for when an unexpected error occurs whilst adding the file to the audit table."""


class VaccineTypePermissionsError(Exception):
    """A custom exception for when the supplier does not have the necessary vaccine type permissions."""


class InvalidFileKeyError(Exception):
    """A custom exception for when the file key is invalid."""


class UnhandledSqsError(Exception):
    """A custom exception for when an unexpected error occurs whilst sending a message to SQS."""
