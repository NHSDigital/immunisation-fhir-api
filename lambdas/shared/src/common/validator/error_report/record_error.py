class ErrorReport:
    def __init__(
        self,
        code: int = None,
        message: str = None,
        row: int = None,
        field: str = None,
        details: str = None,
        summarise: bool = False,
        error_level: int = None,
    ):
        self.code = code
        self.message = message
        self.row = row
        self.field = field
        self.details = details
        self.summarise = summarise
        # these are set when the error is added to the report
        self.error_group = None
        self.name = None
        self.id = None
        self.error_level = error_level

    def __repr__(self):
        return f"<ErrorReport code={self.code}, field={self.field}, message={self.message!r}, details={self.details!r}>"

    # function to return the object as a dictionary
    def to_dict(self):
        ret = {"code": self.code, "message": self.message}
        if not self.summarise:
            ret.update({"row": self.row, "field": self.field, "details": self.details})
        return ret


# record exception capture
class RecordError(Exception):
    def __init__(self, code=None, message=None, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def __str__(self):
        return repr((self.code, self.message, self.details))

    def __repr__(self):
        return repr((self.code, self.message, self.details))
