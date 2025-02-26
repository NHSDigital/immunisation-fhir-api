# Test application file
from pathlib import Path
from src.Converter import Converter
from copy import deepcopy
from decimal import Decimal
import json
import time
import os
import unittest
import boto3


# FHIR_data_folder = Path("C:/Source Code/Vaccs to JSON Converter/FHIR-data")
# filename = FHIR_data_folder / "vaccination7.json"


# def load_json_data(filename: str):
#     """Load the json data"""
#     data_path = f"{os.path.dirname(os.path.abspath(__file__))}/../sample_data"
#     immunization_file_path = f"{data_path}/{filename}"
#     with open(immunization_file_path, "r", encoding="utf-8") as f:
#         return json.load(f, parse_float=Decimal)


class TestConversionToFHIR(unittest.TestCase):

    def test_fhir_converter_json_direct_data(self):
        """it should convert data to flat fhir"""

        json_data = json.dumps(
            {
                "resourceType": "Immunization",
                "contained": [
                    {
                        "resourceType": "Practitioner",
                        "id": "Pract1",
                        "": [{"family": "Nightingale", "given": ["Florence"]}],
                    },
                    {
                        "resourceType": "Patient",
                        "id": "Pat1",
                        "": [
                            {"system": "https://fhir.nhs.uk/Id/nhs-number", "vaue": "9000000009"},
                            {"system": "https://supplierABC/patientIndex", "value": "X12841"},
                        ],
                        "name": [
                            {"use": "maiden", "family": "Barnes", "given": ["Sarah", "Jane"]},
                            {"use": "official", "family": "Taylor", "given": ["Sarah", "Jane"]},
                        ],
                        "gender": "male",
                        "birthDate": "1965-02-28",
                        "address": [{"use": "old", "text": "No fixed abode"}, {"postalCode": "EC1A 1BB"}],
                    },
                ],
                "extension": [
                    {
                        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                        "valueCodeableConcept": {
                            "coding": [
                                {
                                    "extension": [
                                        {
                                            "url": "http://hl7.org/fhir/StructureDefinition/coding-sctdescid",
                                            "valueId": "2837371000000119",
                                        }
                                    ],
                                    "system": "http://snomed.info/sct",
                                    "code": "1324681000000101",
                                    "display": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)",
                                }
                            ]
                        },
                    }
                ],
                "identifier": [{"system": "https://supplierABC/identifiers/vacc", "value": "ACME-vac456"}],
                "status": "completed",
                "vaccineCode": {
                    "coding": [
                        {
                            "system": "http://dm+d.org",
                            "code": "39116211000001106",
                            "display": "Generic COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (product)",
                            "userSelected": "true",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "39114911000001105",
                            "display": "COVID-19 Vaccine Vaxzevria (ChAdOx1 S [recombinant]) not less than 2.5x100,000,000 infectious units/0.5ml dose suspension for injection multidose vials (AstraZeneca UK Ltd) (product)",
                        },
                    ],
                    "text": "AstraZeneca UK Ltd Vaxzevria 0.5ml dose suspension for injection",
                },
                "patient": {
                    "reference": "#Pat1",
                    "type": "Patient",
                    "identifier": {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9000000009"},
                    "display": "TAYLOR, Sarah",
                },
                "occurrenceDateTime": "2021-02-07T13:28:17.271+00:00",
                "recorded": "2021-02-07",
                "primarySource": "true",
                "manufacturer": {"display": "AstraZeneca Ltd"},
                "location": {
                    "identifier": {"value": "X99999", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}
                },
                "lotNumber": "4120Z001",
                "expirationDate": "2021-07-02",
                "site": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "368208006",
                            "display": "Left upper arm structure (body structure)",
                        }
                    ]
                },
                "route": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "78421000",
                            "display": "Intramuscular route (qualifier value)",
                        }
                    ]
                },
                "doseQuantity": {
                    "value": 0.5,
                    "unit": "milliliter",
                    "system": "http://unitsofmeasure.org",
                    "code": "ml",
                },
                "performer": [
                    {
                        "actor": {
                            "reference": "#Pract1",
                            "identifier": {"system": "https://fhir.hl7.org.uk/Id/nmc-number", "value": "5566789"},
                            "display": "NIGHTINGALE, Florence",
                        }
                    },
                    {
                        "actor": {
                            "type": "Organization",
                            "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
                        }
                    },
                ],
                "reasonCode": [{"coding": [{"code": "443684005", "system": "http://snomed.info/sct"}]}],
                "protocolApplied": [
                    {
                        "targetDisease": [
                            {
                                "coding": [
                                    {
                                        "system": "http://snomed.info/sct",
                                        "code": "840539006",
                                        "display": "Disease caused by severe acute respiratory syndrome coronavirus 2 (disorder)",
                                    }
                                ]
                            }
                        ],
                        "doseNumberPositiveInt": 1,
                    }
                ],
            }
        )

        start = time.time()
        # print(json_data)

        FHIRConverter = Converter(json_data)
        FlatFile = FHIRConverter.runConversion(False, True)

        flatJSON = json.dumps(FlatFile)

        if len(flatJSON) > 0:
            print(flatJSON)

        errorRecords = FHIRConverter.getErrorRecords()

        if len(errorRecords) > 0:
            print("Converted With Errors")
            print(errorRecords)
        else:
            print("Converted Successfully")

        end = time.time()
        print(end - start)
