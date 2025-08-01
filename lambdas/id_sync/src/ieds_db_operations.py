from boto3.dynamodb.conditions import Key
from os_vars import get_ieds_table_name
from common.aws_dynamodb import get_dynamodb_table
from common.clients import logger
from exceptions.id_sync_exception import IdSyncException
import json

ieds_table = None


def get_ieds_table():
    """Get the IEDS table."""
    global ieds_table
    if ieds_table is None:
        ieds_tablename = get_ieds_table_name()
        ieds_table = get_dynamodb_table(ieds_tablename)
    return ieds_table


def ieds_check_exist(id: str) -> bool:
    """Check if a record exists in the IEDS table for the given ID."""
    search_patient_pk = f"Patient#{id}"

    # Only fetch 1 record to check existence
    response = get_ieds_table().query(
        KeyConditionExpression=Key("PK").eq(search_patient_pk),
        Limit=1
    )
    return response.get("Count", 0) > 0


def ieds_update_patient_id(old_id: str, new_id: str) -> dict:
    """Update the patient ID in the IEDS table."""
    logger.info(f"ieds_update_patient_id. Update patient ID from {old_id} to {new_id}")
    if not old_id or not new_id or not old_id.strip() or not new_id.strip():
        return {"status": "error", "message": "Old ID and New ID cannot be empty"}

    if old_id == new_id:
        return {"status": "success", "message": f"No change in patient ID: {old_id}"}

    try:
        # Update the table with new id
        response = get_ieds_table().update_item(
            Key={"PK": f"Patient#{old_id}"},
            UpdateExpression="SET PK = :new_id",
            ExpressionAttributeValues={":new_id": f"Patient#{new_id}"}
        )

        # Check update successful
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {
                "status": "success",
                "message": f"Updated IEDS, patient ID: {old_id} to {new_id}"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to update patient ID: {old_id}"
            }

    except Exception as e:
        logger.exception("Error updating patient ID")
        raise IdSyncException(
            message=f"Error updating patient Id from :{old_id} to {new_id}",
            nhs_numbers=[old_id, new_id],
            exception=e
        )
        raise e


def test_ieds_insert_patient(patient_id: str) -> dict:  # NOSONAR
    """Test function for inserting patient ID."""
    logger.info("insert to db...")
    # write the patient id to table
    result = get_ieds_table().put_item(Item={
                    "PK": f"Patient#{patient_id}",
                    "PatientPK": f"Patient#{patient_id}",
                    "PatientSK": f"Patient#{patient_id}",
                    "Resource": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "iucds", "given": ["Russell"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9726629101"}], "name": [{"family": "VAREY", "given": ["DIANA"]}], "gender": "unknown", "birthDate": "2021-10-24", "address": [{"postalCode": "DN15 8EZ"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ieds.england.nhs.uk/", "value": "a7e06f66-339f-4b81-b2f6-016b88bfc422"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001100", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2025-05-27T14:53:26.271+00:00", "recorded": "2025-07-10T11:25:56.000+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"identifier": {"value": "X8E5B", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVAPITEST", "expirationDate": "2025-06-01", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"value": 0.5, "unit": "milliliter", "system": "http://unitsofmeasure.org", "code": "ml"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "display": "UNIVERSITY HOSPITAL OF WALES", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"}}}], "reasonCode": [{"coding": [{"code": "443684005", "display": "Disease outbreak (event)", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "55735004", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder)"}]}], "doseNumberPositiveInt": 11}], "id": "088414ed-7d3d-40a5-9968-b3d2b9a266b2"}',
                    "IdentifierPK": "https://www.ieds.england.nhs.uk/#a7e06f66-339f-4b81-b2f6-016b88bfc422",
                    "Operation": "CREATE",
                    "Version": "1",
                    "SupplierSystem": "RAVS",
                })

    logger.info(f"Test result: {result}")
    return result
