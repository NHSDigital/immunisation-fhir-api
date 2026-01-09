import uuid

def get_search_get_url_header(context):
    context.url = context.baseUrl + "/Immunization"
    context.headers =  {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']

def get_search_post_url_header(context):
    context.url = context.baseUrl + "/Immunization/_search"
    context.headers =  {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']
    
def get_create_post_url_header(context):
    context.url = context.baseUrl+ "/Immunization"    
    context.headers = {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/fhir+json',
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']
    
def get_delete_url_header(context):
    context.url = context.baseUrl + "/Immunization"    
    context.headers = {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/fhir+json',
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']
    
def get_update_url_header(context, tag:str):
    context.url = context.baseUrl + "/Immunization"    
    context.headers = {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/fhir+json',
        'E-Tag': tag,
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']
    
def get_read_url_header(context):
    context.url = context.baseUrl + f"/Immunization/{context.ImmsID}?_summary"    
    context.headers = {
        'X-Correlation-ID': str(uuid.uuid4()),
        'X-Request-ID': str(uuid.uuid4()),
        'Accept': 'application/fhir+json',
        'Content-Type': 'application/fhir+json',
        'Authorization': 'Bearer ' + context.token
        }
    context.corrID = context.headers['X-Correlation-ID']
    context.reqID = context.headers['X-Request-ID']
