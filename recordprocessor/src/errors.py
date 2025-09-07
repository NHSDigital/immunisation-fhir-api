"""Custom exceptions for the Record Processor."""


class NoOperationPermissions(Exception):
    """A custom exception for when the supplier has no permissions for any of the requested operations."""


class InvalidHeaders(Exception):
    """A custom exception for when the file headers are invalid."""


class InvalidEncoding(Exception):
    """A custom exception for when the file encoding is invalid."""


class UnhandledAuditTableError(Exception):
    """A custom exception for when an unexpected error occurs whilst adding the file to the audit table."""
