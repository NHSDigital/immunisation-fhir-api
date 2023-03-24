'''
APP for fastapi
'''
import os
from fastapi import FastAPI

from fhir_api.routes import (
    root,
    health,
    dynamodb,
)

from fhir_api.models.fhir_r4.common import Reference, Identifier

Reference.update_forward_refs(identifier=Identifier)


app = FastAPI(
    title=os.getenv('FASTAPI_TITLE', 'Immunization Fhir API'),
    description=os.getenv(
        'FASTAPI_DESC', 'API'),
    version=os.getenv('VERSION', 'DEVELOPMENT'),
    root_path='/internal-dev-sandbox.api.service.nhs.uk/immunisation-fhir-api-pr-12/',
    docs_url="/documentation",
    redoc_url="/redocumentation")


# ENDPOINT ROUTERS
app.include_router(root.router)
app.include_router(health.router)
app.include_router(dynamodb.router)
