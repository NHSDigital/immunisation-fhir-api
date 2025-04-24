"""Base Exceptions that can be used across all collections"""

# pylint: disable=W0231

from typing import Type
import fastapi
from fastapi.responses import JSONResponse
from fhir_api.models.errors import (
    NotFoundError,
    AlreadyExistsError,
    WebSocketError,
    BaseError,
    BaseIdentifiedError,
)


class BaseAPIException(Exception):
    """Base Error for custom API exceptions"""

    message = "Exception Occured"
    code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    model = BaseError

    def __init__(self, **kwargs):
        kwargs.setdefault("message", self.message)
        self.message = kwargs["message"]
        self.data = self.model(**kwargs)

    def response(self):
        return JSONResponse(content=self.data.dict(), status_code=self.code)

    @classmethod
    def response_model(cls):
        return {cls.code: {"model": cls.model}}


class BaseIdentifiedException(BaseAPIException):
    """Base error for exceptions related with entities, uniquely identified"""

    message = "Entity error"
    code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    model = BaseIdentifiedError

    def __init__(self, identifier, **kwargs):
        super().__init__(identifier=identifier, **kwargs)


class NotFoundException(BaseIdentifiedException):
    """Base error for exceptions raised because an entity does not exist"""

    message = "The entity does not exist"
    code = fastapi.status.HTTP_404_NOT_FOUND
    model = NotFoundError


class AlreadyExistsException(BaseIdentifiedException):
    """Base error for exceptions raised because an entity already exists"""

    message = "The entity already exists"
    code = fastapi.status.HTTP_409_CONFLICT
    model = AlreadyExistsError


class WebSocketException(BaseAPIException):
    """Base Error for websocket exceptions"""

    message = "Websocket encountered an error"
    code = fastapi.status.HTTP_418_IM_A_TEAPOT
    model = WebSocketError


def get_exception_responses(*args: Type[BaseAPIException]) -> dict:
    """return a dict of responses used on FastAPI endpoint"""
    responses = {}
    for cls in args:
        responses.update(cls.response_model())
    return responses
