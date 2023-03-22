'''
APP for fastapi
'''
import os
from fastapi import FastAPI

from fhir_api.routes import root
from fhir_api.routes import endpoints


app = FastAPI(
    title=os.getenv('FASTAPI_TITLE', 'Immunization Fhir API'),
    description=os.getenv(
        'FASTAPI_DESC', 'API'),
    version=os.getenv('VERSION', 'SANDBOX'))


# ENDPOINT ROUTERS
app.include_router(root.router)
app.include_router(endpoints.router)
