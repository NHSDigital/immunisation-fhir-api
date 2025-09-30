import inspect
from responses import logger


class ServiceReturn:
    def __init__(
        self,
        status: int = 200,
        message: str = "OK",
        value: any = None,
        exception: Exception = None
    ):
        self.status = status
        self.message = message
        self.value = value
        self.exception = exception
        self.call_location = self._get_call_location()

        if self.status != 200 and (self.exception or self.message):
            msg = {
                "status": self.status,
                "Message": self.message,
                "Exception": self.exception,
                "Location": self.call_location
            }
            logger.warning(f"ServiceReturn : {msg}")

    def _get_call_location(self):
        # Get the name of the function 2 frames up
        frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(frame)
        if len(outer_frames) >= 3:
            caller_frame = outer_frames[2]
            return f"{caller_frame.function} ({caller_frame.filename}:{caller_frame.lineno})"
        return "Unknown"

    def to_string(self):
        exception_msg = f"{type(self.exception).__name__}: {self.exception}" if self.exception else "No exception"
        error_msg = f"{self.message}" if self.message else ""
        return f"{self.call_location}." \
               f"{error_msg} " \
               f"{exception_msg})"

    def __bool__(self):
        return self.exception is None

    @property
    def is_success(self) -> bool:
        return self.exception is None


# an example function that uses ServiceReturn
def my_divide(a: int, b: int) -> ServiceReturn:
    try:
        result = a / b
        return ServiceReturn(value=result)
    except Exception as e:
        return ServiceReturn(
            status=500,
            message="Division failed",
            exception=e
        )


# example of usage
# Test
result = my_divide(10, 0)


if result:  # or result.is_success as below
    print(f"Result: {result.value}")
else:
    print(f"Error: {result.to_string()}")

# Optional explicit check
if result.is_success:
    print("Division succeeded.")
