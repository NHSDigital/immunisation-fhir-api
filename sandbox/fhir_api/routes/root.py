""" root """

import os

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


router = APIRouter()


@router.get('/')
def root():
    """ root """
    return PlainTextResponse(
        os.getenv('FASTAPI_TITLE', 'FHIR API')
        )
