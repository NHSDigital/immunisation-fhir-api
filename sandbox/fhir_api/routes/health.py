from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix='/health')


@router.get('',
            description="Health check endpoint only returns 200",
            tags=['health'])
def health():
    return PlainTextResponse(None, 200)
