''' Populate Table with fake data '''

from datetime import datetime, timedelta
from uuid import uuid4
from random import choice, randint, choices
from string import ascii_letters, digits

import requests
import json


RANDOM_WORDS = requests.get(
    'https://www.mit.edu/~ecprice/wordlist.10000').text.split('\n')


def generate_identifier():
    id_dict = {}
    id_dict['use'] = choice(["usual","official","temp","secondary","old"])
    id_dict['system'] = "https://supplierABC/identifiers/vacc"
    id_dict['value'] = str(randint(1000000,9999999))
    return id_dict

def generate_status():
    return choice(["completed", "entered-in-error", "not-done"])

def generate_coding_concept():
    cc_dict = {}
    cc_dict['system'] = 'http://snomed.info/sct'
    cc_dict['code'] = str(randint(1000000,9999999))
    cc_dict['display'] = " ".join(choices(RANDOM_WORDS, k=15))
    return cc_dict

def generate_coding_list():
    return {'coding': [generate_coding_concept() for i in range(randint(1,2))]}

def generate_reference(ref_type: str, display: bool = False):
    ref_dict = {}
    ref_dict['reference'] = f"urn:uuid:{uuid4()}"
    ref_dict['type'] = ref_type
    ref_dict['identifier'] = generate_identifier()
    if display:
        ref_dict['display'] = f"{choice(RANDOM_WORDS)}-{choice(RANDOM_WORDS)}"

    return ref_dict

def generate_dose_quantity():
    dq_dict = {}
    dq_dict['system'] = 'http://snomed.info/sct'
    dq_dict['value'] = randint(1, 100)
    dq_dict['unit'] = " ".join(choices(RANDOM_WORDS, k=7))
    dq_dict['code'] = str(randint(1000000000000000, 9999999999999999))
    return dq_dict

def generate_protocol_applied():
    return [
        {
            "doseNumberPositiveInt": randint(1,10)
        }
    ]

def generate_random_time():
    return (datetime.utcnow() - timedelta(
        days=randint(0, 1000),
        hours=randint(0, 23),
        minutes=randint(0, 59),
        seconds=randint(0, 59),
    )).isoformat()

def generate_random_string(str_size):
    return ''.join(choice(ascii_letters + digits) for x in range(str_size))

def generate_immunization_data():
    data = {
        'resourceType': 'Immunization',
        'identifier': [generate_identifier() for i in range(randint(1,2))],
        'status': generate_status(),
        'vaccineCode': generate_coding_list(), 
        'patient': generate_reference('Patient'),
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

def generate_human_name():
    hn_dict = {}
    hn_dict['use'] = choice(["usual", "official", "temp", "nickname", "anonymous", "old", "maiden"])
    hn_dict['family'] = choice(RANDOM_WORDS)
    hn_dict['given'] = [choice(RANDOM_WORDS) for i in range(randint(1,3))]
    if choice([True, False]):
        hn_dict['prefix'] = choice(RANDOM_WORDS)
    if choice([True, False]):
        hn_dict['suffix'] = choice(RANDOM_WORDS)
    hn_dict['period'] = {
        'start': generate_random_time(),
        'end': '9999-01-01'
    }
    return hn_dict

def generate_contact_point():
    tc_dict = {}
    tc_dict['system'] = choice(["phone", "fax", "email", "pager", "url", "sms", "other"])
    tc_dict['use'] = choice(['home', 'work', 'temp', 'old', 'mobile'])
    tc_dict['value'] = f"0{randint(0,10)} {randint(1000, 9999)} {randint(1000, 9999)}"
    tc_dict['rank'] = str(randint(1,10))
    tc_dict['period'] = {
        'end': generate_random_time()
    }
    return tc_dict

def generate_postal_code():
    return f"{''.join(choices(ascii_letters, k=2))}{''.join(choices(digits, k=2))} {''.join(choice(digits))}{''.join(choices(ascii_letters, k=2))}".upper()

def generate_address():
    add_dict = {}
    add_dict['use'] = choice(["home", "work", "temp", "old", "billing"])
    add_dict['type'] = choice(["postal", "physical", "both"])
    add_dict['line'] = [f"{randint(1,999)} {' '.join(choices(RANDOM_WORDS, k=randint(1,3)))}"]
    add_dict['city'] = choice(RANDOM_WORDS)
    add_dict['district'] = choice(RANDOM_WORDS)
    add_dict['state'] = choice(RANDOM_WORDS)
    add_dict['postalCode'] = generate_postal_code()
    add_dict['text'] = f"{' '.join(add_dict['line'])} {add_dict['city']}, {add_dict['district']}, {add_dict['state']}, {add_dict['postalCode']}"
    if choice([True, False]):
        add_dict['country'] = choice(RANDOM_WORDS)
    add_dict['period'] = {
        'start': generate_random_time(),
    }
    if choice([True, False]):
        add_dict['period']['end'] = generate_random_time()
    return add_dict

def generate_patient_data():
    data = {
        'resourceType': 'Patient',
        'identifier': generate_identifier(),
        'active': choice([True, False]),
        'name': [generate_human_name() for i in range(randint(1,3))],
        'telecom': [generate_contact_point() for i in range(randint(1,3))],
        'gender': choice(["male", "female", "other", "unknown"]),
        'birthDate':  generate_random_time().split('T')[0],
        'deceasedBoolean': choice([True, False]),
        'address': generate_address(),
        'contact': {
            'relationship': generate_coding_list(),
            'name': [generate_human_name() for i in range(randint(1,3))],
            'telecom': [generate_contact_point() for i in range(randint(1,3))],
            'address': generate_address(),
        'gender': choice(["male", "female", "other", "unknown"]),
        }
    }
    data['contact']['period'] = {
        'start': generate_random_time(),
    }
    if choice([True, False]):
        data['contact']['period']['end'] = generate_random_time()
    data['managingOrganization'] = generate_reference('Organization')

    return data

def generate_immunization_records(nhs_number):
    record_dict = {}
    record_dict['nhsNumber'] = nhs_number 
    record_dict['fullUrl'] = f"urn:uuid:{uuid4()}"
    record_dict['entityType'] = 'immunization'
    record_dict['data'] = generate_immunization_data()
    record_dict['dateModified'] = datetime.now().isoformat()
    return record_dict

def generate_patient_records(nhs_number):
    patient_dict = {}
    patient_dict['nhsNumber'] = nhs_number 
    patient_dict['fullUrl'] = f"urn:uuid:{uuid4()}"
    patient_dict['entityType'] = 'patient'
    patient_dict['data'] = generate_patient_data()
    patient_dict['dateModified'] = datetime.now().isoformat()
    return patient_dict

def generate_record_data():
    nhs_number = str(randint(10000000,99999999))
    return (
        generate_patient_records(nhs_number=nhs_number), 
        generate_immunization_records(nhs_number=nhs_number)
    )

if __name__ == '__main__':
    nhs_number = str(randint(10000000,99999999))
    print(json.dumps(generate_immunization_records(nhs_number), indent=4))
    print(json.dumps(generate_patient_records(nhs_number), indent=4))