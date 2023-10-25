import json
from time import time
from csv_to_model import read_csv_to_immunizations
from model_to_fhir import convert_to_fhir
from boto3 import resource
from boto3 import client


# This is yet to be integrated with main logic
def lambda_handler(_event, _context):
    s3_client = client("s3")
    records = _event.get("Records", [])
    s3_event = records[0].get("s3", {})
    source_bucket_name = s3_event.get("bucket", {}).get("name")
    bucket_key_name = s3_event.get("object", {}).get("key")

    dest_bucket_name = source_bucket_name.replace("source", "destination")
    output_bucket = resource("s3").Bucket(dest_bucket_name)

    # Read the contents of the CSV file from S3
    try:
        response = s3_client.get_object(Bucket=source_bucket_name, Key=bucket_key_name)
        csv_data = response["Body"].read().decode("utf-8")

        immunizations = read_csv_to_immunizations(csv_data)

        for immunization in immunizations:

            fhir_imms = convert_to_fhir(immunization)

            expected_json = json.loads(fhir_imms.get_immunization())
            expected_json["patient"] = json.loads(fhir_imms.get_patient())
            expected_json["reportOrigin"] = json.loads(fhir_imms.get_report_origin())
            expected_json["reasonCode"] = json.loads(fhir_imms.get_reason_code())
            expected_json["recorded"] = fhir_imms.get_recorded()
            expected_json["manufacturer"] = json.loads(fhir_imms.get_manufacturer())
            expected_json["performer"] = fhir_imms.get_actor()
            # Add "resourceType" to the "location" element
            expected_json["location"]["resourceType"] = "Location"
            print(json.dumps(expected_json))

        # Write some placeholder bytestring data to a file in the bucket
        filename = f"output_report_{int(time())}.txt"
        data = (
            f"Test file to see if the lambda writes to the correct S3 bucket. "
            f"This was the name of the original file: {bucket_key_name}. "
            f"content of file: {immunizations}. "
            f"If our AWS bill skyrockets, this file has been written to the wrong bucket!"
        )

        output_bucket.put_object(Body=data, Key=filename)

        return {"statusCode": 200}
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return {"statusCode": 500, "body": "Error reading CSV file from S3."}
