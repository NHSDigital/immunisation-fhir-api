import unittest
import json
from unittest.mock import patch
from transform_vaccine_map import transform_vaccine_map


# Import the sample input from the sample_data module
with open("./tests/sample_data/disease_mapping.json") as f:
    sample_map = json.load(f)


class TestTransformVaccineMap(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()

    def test_transform_vaccine_map(self):
        result = transform_vaccine_map(sample_map)
        # Check that all vaccine keys are present and map to the correct diseases
        for entry in sample_map:
            self.assertIn(entry["vacc_type"], result["vaccine"])
            self.assertEqual(result["vaccine"][entry["vacc_type"]], entry["diseases"])
        # Check that all disease keys are present and map to the correct vaccine
        for entry in sample_map:
            disease_codes = ':'.join(sorted(d["code"] for d in entry["diseases"]))
            self.assertIn(disease_codes, result["disease"])
            self.assertEqual(result["disease"][disease_codes], entry["vacc_type"])

    def test_disease_to_vacc(self):
        """ Test that the disease to vaccine mapping is correct."""
        expected_disease_to_vacc = {
            '840539006': 'COVID19',
            '6142004': 'FLU',
            '240532009': 'HPV',
            '14189004:36653000:36989005': 'MMR',
            '14189004:36653000:36989005:38907003': 'MMRV',
            '55735004': 'RSV',
            '27836007': 'PERTUSSIS',
            '4740000': 'SHINGLES',
            '16814004': 'PCV13',
            '397430003:398102009:76902006': '3in1',
            '23511006': 'MENACWY'
        }
        result = transform_vaccine_map(sample_map)
        self.assertEqual(result["disease"], expected_disease_to_vacc)

    def test_vacc_to_diseases(self):
        expected_vacc_to_diseases = {
            "COVID19": [
                {
                    "code": '840539006',
                    "term": 'Disease caused by severe acute respiratory syndrome coronavirus 2'
                }
            ],
            "FLU": [
                {
                    "code": '6142004',
                    "term": 'Influenza caused by seasonal influenza virus (disorder)'
                }
            ],
            "HPV": [
                {
                    "code": '240532009',
                    "term": 'Human papillomavirus infection'
                }
            ],
            "MMR": [
                {
                    "code": '14189004',
                    "term": 'Measles (disorder)'
                },
                {
                    "code": '36989005',
                    "term": 'Mumps (disorder)'
                },
                {
                    "code": '36653000',
                    "term": 'Rubella (disorder)'
                }
            ],
            "MMRV": [
                {
                    "code": '14189004',
                    "term": 'Measles (disorder)'
                },
                {
                    "code": '36989005',
                    "term": 'Mumps (disorder)'
                },
                {
                    "code": '36653000',
                    "term": 'Rubella (disorder)'
                },
                {
                    "code": '38907003',
                    "term": 'Varicella (disorder)'
                }
            ],
            "RSV": [
                {
                    "code": '55735004',
                    "term": 'Respiratory syncytial virus infection (disorder)'
                }
            ],
            "PERTUSSIS": [
                {
                    "code": '27836007',
                    "term": 'Pertussis (disorder)'
                }
            ],
            "SHINGLES": [
                {
                    "code": '4740000',
                    "term": 'Herpes zoster'
                }
            ],
            "PCV13": [
                {
                    "code": '16814004',
                    "term": 'Pneumococcal infectious disease'
                }
            ],
            "3in1": [
                {
                    "code": '398102009',
                    "term": 'Acute poliomyelitis'
                },
                {
                    "code": '397430003',
                    "term": 'Diphtheria caused by Corynebacterium diphtheriae'
                },
                {
                    "code": '76902006',
                    "term": 'Tetanus (disorder)'
                }
            ],
            "MENACWY": [
                {
                    "code": '23511006',
                    "term": 'Meningococcal infectious disease'
                }
        ]
            }

        result = transform_vaccine_map(sample_map)
        self.assertEqual(result["vaccine"], expected_vacc_to_diseases)
