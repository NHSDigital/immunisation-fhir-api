def get_status_handler(_event, _context):
    response = {
        "statusCode": 200,  # HTTP status code
        "body": "OK"
    }
    return response
