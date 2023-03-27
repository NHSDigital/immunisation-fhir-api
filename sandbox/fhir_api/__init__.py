'''
APP for fastapi
'''
import os
from fastapi import FastAPI

from fhir_api.routes import (
    root,
    dynamodb,
    status_endpoints,
)

from fhir_api.models.fhir_r4.common import Reference, Identifier

Reference.update_forward_refs(identifier=Identifier)


app = FastAPI(
    title=os.getenv('FASTAPI_TITLE', 'Immunization Fhir API'),
    description=os.getenv(
        'FASTAPI_DESC', 'API'),
    version=os.getenv('VERSION', 'DEVELOPMENT'),
    root_path=f'/{os.getenv("SERVICE_BASE_PATH")}/',
    docs_url="/documentation",
    redoc_url="/redocumentation")


# ENDPOINT ROUTERS
app.include_router(root.router)
app.include_router(dynamodb.router)
app.include_router(status_endpoints.router)
