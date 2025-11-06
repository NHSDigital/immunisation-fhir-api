class IdSyncException(Exception):
    """Custom exception for ID Sync errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
