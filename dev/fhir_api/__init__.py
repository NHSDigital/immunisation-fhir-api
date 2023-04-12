'''
APP for fastapi
'''
import os
from fastapi import FastAPI
from mangum import Mangum
from fhir_api.routes import (
    immunisation,
    root,
    health,
    snomed,
)

from fhir_api.models.fhir_r4.common import Reference, Identifier

Reference.update_forward_refs(identifier=Identifier)


app = FastAPI(
    title=os.getenv('FASTAPI_TITLE', 'Immunization Fhir API'),
    description=os.getenv(
        'FASTAPI_DESC', 'API'),
    version=os.getenv('VERSION', 'DEVELOPMENT'))


# ENDPOINT ROUTERS
app.include_router(root.router)
app.include_router(health.router)
app.include_router(immunisation.router)
app.include_router(snomed.router)

hander = Mangum(app)
