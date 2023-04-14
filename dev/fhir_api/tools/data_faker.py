''' Populate Table with fake data '''
# flake8: noqa E501

from datetime import datetime, timedelta
from uuid import uuid4
from random import choice, randint, choices
from string import ascii_letters, digits

import json
import requests

# Get random words list from URL
RANDOM_WORDS = requests.get(
    'https://www.mit.edu/~ecprice/wordlist.10000', timeout=60).text.split('\n')


def generate_identifier() -> dict:
    ''' Generate Identifier Dictionary '''
    id_dict = {}
    id_dict['use'] = choice(["usual", "official", "temp", "secondary", "old"])
    id_dict['system'] = "https://supplierABC/identifiers/vacc"
    id_dict['value'] = str(randint(1000000, 9999999))
    return id_dict


def generate_status() -> str:
    ''' Generate Status '''
    return choice(["completed", "entered-in-error", "not-done"])


def generate_coding_concept() -> dict:
    ''' Generate coding concept '''
    cc_dict = {}
    cc_dict['system'] = 'http://snomed.info/sct'
    cc_dict['code'] = str(randint(1000000, 9999999))
    cc_dict['display'] = " ".join(choices(RANDOM_WORDS, k=15))
    return cc_dict


def generate_coding_list() -> dict[str: list]:
    ''' Generate List of Coding Concepts '''
    return {'coding': [
        generate_coding_concept() for i in range(randint(1, 2))]
    }


def generate_reference(ref_type: str, display: bool = False, id=uuid4()) -> dict:
    '''
    Generate Reference Dictionary

    Parameters:
        ref_type: string -- Reference Type of Reference (
            i.e Patient, Organization, etc)
        display: bool -- Boolean to determine whether to include display item
            in dictionary

    Return:
        ref_dict: dict -- Dictionary of all Reference items

    '''
    ref_dict = {}
    ref_dict['reference'] = f"urn:uuid:{id}"
    ref_dict['type'] = ref_type
    ref_dict['identifier'] = generate_identifier()
    if display:
        ref_dict['display'] = f"{choice(RANDOM_WORDS)}-{choice(RANDOM_WORDS)}"

    return ref_dict


def generate_dose_quantity() -> dict:
    ''' Generate Dose Quantity Dictionary '''
    dq_dict = {}
    dq_dict['system'] = 'http://snomed.info/sct'
    dq_dict['value'] = randint(1, 100)
    dq_dict['unit'] = " ".join(choices(RANDOM_WORDS, k=7))
    dq_dict['code'] = str(randint(1000000000000000, 9999999999999999))
    return dq_dict


def generate_protocol_applied() -> list[dict]:
    ''' Generate Protocol Applied Dictionary '''
    return [
        {
            "doseNumberPositiveInt": randint(1, 10)
        }
    ]


def generate_random_time(before=0, after=1000) -> str:
    ''' Generates a random datetime (upto 1000 days ago) in isoformat '''
    random_date = (datetime.utcnow() - timedelta(
        days=randint(before, after),
        hours=randint(0, 23),
        minutes=randint(0, 59),
        seconds=randint(0, 59),
    )).isoformat()
    return f"{random_date}Z"


def generate_random_string(str_size: int) -> str:
    '''
    Generate Random String

    Parameters:
        str_size: integer -- Integer for how many chars are in string
    '''
    return ''.join(choice(ascii_letters + digits) for x in range(str_size))


def generate_period_data() -> dict():
    ''' Generate random period start and end time '''
    period_dict = {'start': generate_random_time(1000,2000)}
    if choice([True, False]):
        period_dict['end'] = generate_random_time()
    
    return period_dict


def generate_immunization_data(patient_id=None) -> dict:
    '''
    Generate FHIR immunization Data Dictionary

    Returns:
        data: dict -- Dictionary of Randomised Immunization Data
    '''
    data = {
        'resourceType': 'Immunization',
        'identifier': [generate_identifier() for i in range(randint(1, 2))],
        'status': generate_status(),
        'vaccineCode': generate_coding_list(),
        'patient': generate_reference('Patient', id=patient_id),
        'occurrenceDateTime': generate_random_time(),
        'recorded': generate_random_time().split('T')[0],
        'primarySource': choice([True, False]),
        'manufacturer': generate_reference('Manufacturer'),
        'lotNumber': generate_random_string(4).upper(),
        'expirationDate': generate_random_time().split('T')[0],
        'site': generate_coding_list(),
        'route': generate_coding_list(),
        'doseQuantity': generate_dose_quantity(),
        'reportOrigin': {},
        'performer': [
            {
                'actor': generate_reference('Organization', display=True)
            }
        ],
        'reasonCode': [generate_coding_list()],
        'protocolApplied': generate_protocol_applied()
    }
    return data


def generate_human_name() -> dict:
    ''' Generate FHIR Human Name Dictionary '''
    hn_dict = {}
    hn_dict['use'] = choice(
        [
            "usual", "official", "temp", "nickname",
            "anonymous", "old", "maiden"
        ]
    )
    hn_dict['family'] = choice(RANDOM_WORDS)
    hn_dict['given'] = [choice(RANDOM_WORDS) for i in range(randint(1, 3))]
    if choice([True, False]):
        hn_dict['prefix'] = [choice(RANDOM_WORDS)]
    if choice([True, False]):
        hn_dict['suffix'] = [choice(RANDOM_WORDS)]
    hn_dict['period'] = generate_period_data()
    return hn_dict


def generate_contact_point() -> dict:
    ''' Generate Contact Point Dictionary '''
    tc_dict = {}
    tc_dict['system'] = choice(
        ["phone", "fax", "email", "pager", "url", "sms", "other"])
    tc_dict['use'] = choice(['home', 'work', 'temp', 'old', 'mobile'])
    tc_dict['value'] = f"0{randint(0,10)} {randint(1000, 9999)} {randint(1000, 9999)}"
    tc_dict['rank'] = str(randint(1, 10))
    tc_dict['period'] = generate_period_data()
    return tc_dict


def generate_postal_code() -> str:
    ''' Generate Random UK Standard Postal Code '''
    return f"{''.join(choices(ascii_letters, k=2))}{''.join(choices(digits, k=2))} {''.join(choice(digits))}{''.join(choices(ascii_letters, k=2))}".upper()


def generate_address() -> dict:
    ''' Generate Address Dictionary '''
    add_dict = {}
    add_dict['use'] = choice(["home", "work", "temp", "old", "billing"])
    add_dict['type'] = choice(["postal", "physical", "both"])
    add_dict['line'] = f"{randint(1,999)} {' '.join(choices(RANDOM_WORDS, k=randint(1,3)))}"
    add_dict['city'] = choice(RANDOM_WORDS)
    add_dict['district'] = choice(RANDOM_WORDS)
    add_dict['state'] = choice(RANDOM_WORDS)
    add_dict['postalCode'] = generate_postal_code()
    add_dict['text'] = f"{''.join(add_dict['line'])} {add_dict['city']}, {add_dict['district']}, {add_dict['state']}, {add_dict['postalCode']}"
    if choice([True, False]):
        add_dict['country'] = choice(RANDOM_WORDS)
    add_dict['period'] = generate_period_data()
    return add_dict

def generate_random_contact() -> dict:
    ''' Generates random contact info '''
    contact_dict = {
        'relationship': [generate_coding_list()],
        'name': generate_human_name(),
        'telecom': [generate_contact_point() for i in range(randint(1, 3))],
        'address': generate_address(),
        'gender': choice(["male", "female", "other", "unknown"]),
        'period': generate_period_data(),
    }
    return contact_dict

def generate_patient_data() -> dict:
    '''
    Generate Patient Data Dictionary

    Returns:
        data: dict -- Dictionary of Randomised Immunization Data
    '''
    data = {
        'resourceType': 'Patient',
        'identifier': [generate_identifier() for i in range(randint(1, 2))],
        'active': choice([True, False]),
        'name': [generate_human_name() for i in range(randint(1, 3))],
        'telecom': [generate_contact_point() for i in range(randint(1, 3))],
        'gender': choice(["male", "female", "other", "unknown"]),
        'birthDate':  generate_random_time().split('T')[0],
        'deceasedBoolean': choice([True, False]),
        'address': [generate_address() for i in range(randint(1, 3))],
        'contact': [generate_random_contact() for i in range(randint(1,3))],
        'managingOrganization': generate_reference('Organization'),
    }

    return data


def generate_immunization_records(nhs_number, patient_id=None) -> dict:
    '''
    Generate Immunization Record Wrapper

    Parameters:
        nhs_number: str -- NHS Number str

    Returns:
        record_dict: dict -- Dictionary of complete immunization record
    '''
    record_dict = {}
    record_dict['nhsNumber'] = nhs_number
    record_dict['fullUrl'] = f"urn:uuid:{uuid4()}"
    record_dict['entityType'] = 'immunization'
    record_dict['data'] = generate_immunization_data(patient_id=patient_id)
    record_dict['dateModified'] = datetime.now().isoformat()
    record_dict['diseaseType'] = choice(['COVID-19', 'Influenza', 'Pneumococcal'])
    return record_dict


def generate_patient_records(nhs_number) -> dict:
    '''
    Generate Patient Record Wrapper

    Parameters:
        nhs_number: str -- NHS Number str

    Returns:
        record_dict: dict -- Dictionary of complete patient record
    '''
    patient_dict = {}
    patient_dict['nhsNumber'] = nhs_number
    patient_dict['fullUrl'] = f"urn:uuid:{uuid4()}"
    patient_dict['entityType'] = 'patient'
    patient_dict['data'] = generate_patient_data()
    patient_dict['dateModified'] = datetime.now().isoformat()
    return patient_dict


def generate_record_data() -> tuple:
    '''
    Generate Record Data

    Returns:
        tuple -- returns patient and immunization data using the same nhs_number

    '''
    #nhs_number = str(randint(10000000, 99999999))
    nhs_number = "23838008"
    patient_record = generate_patient_records(nhs_number=nhs_number)
    return (
        patient_record,
        generate_immunization_records(nhs_number=nhs_number, patient_id=patient_record['fullUrl'])
    )


if __name__ == '__main__':
    NHS_NUMBER = str(randint(10000000, 99999999))
    for i in generate_record_data():
        print(json.dumps(i, indent=4))
