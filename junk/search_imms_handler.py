def search_imms_handler(event, context):
    # print event and prettify
    print("Hello World")
    return {
        "statusCode": 200,
        "body": "Hello, World from Lambda container!"
    }
