class IdSyncException(Exception):
    """Custom exception for ID Sync errors."""
    def __init__(self, message: str, nhs_numbers: list = None, exception=None):
        self.message = message
        self.nhs_numbers = nhs_numbers
        self.inner_exception = exception
        super().__init__(message)
