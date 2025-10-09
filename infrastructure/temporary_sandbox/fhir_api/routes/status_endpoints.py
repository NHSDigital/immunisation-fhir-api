""" Sandbox endpoints """

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get('/_ping',
            description="Ping check endpoint only returns 200")
def ping():
    """ ping sandbox """
    return PlainTextResponse(None, 200)


@router.get('/_status',
            description="Status check endpoint only returns 200")
def status():
    """ status sandbox """
    data = {"status": "pass", "ping": "pong", "service": "immunisations-fhir-api", "version": "{}"}
    return data


@router.get('/health',
            description="Health check endpoint only returns 200",
            tags=['health'])
def health():
    return PlainTextResponse(None, 200)
