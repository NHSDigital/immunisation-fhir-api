import json
from unittest import mock


# TODO - should we use FakeRedis instead like filenameprocessor?
# TODO - or should we just mock individual hget / hkeys calls?
class MockRedisClient:
    def __init__(self):
        self.mock_data = {
            "vacc_to_diseases": {},
            "diseases_to_vacc": {},
            "supplier_permissions": {}
        }

        self.add_vacc("COVID19", [
            {"code": "840539006", "term": "Disease caused by severe acute respiratory syndrome coronavirus 2"}
        ])
        self.add_vacc("FLU", [
            {"code": "6142004", "term": "Influenza caused by seasonal influenza virus (disorder)"}
        ])
        self.add_vacc("HPV", [
            {"code": "240532009", "term": "Human papillomavirus infection"}
        ])
        self.add_vacc("MMR", [
            {"code": "14189004", "term": "Measles (disorder)"},
            {"code": "36989005", "term": "Mumps (disorder)"},
            {"code": "36653000", "term": "Rubella (disorder)"}
        ])
        self.add_vacc("MMRV", [
            {"code": "14189004", "term": "Measles (disorder)"},
            {"code": "36989005", "term": "Mumps (disorder)"},
            {"code": "36653000", "term": "Rubella (disorder)"},
            {"code": "38907003", "term": "Varicella (disorder)"}
        ])
        self.add_vacc("RSV", [
            {"code": "55735004", "term": "Respiratory syncytial virus infection (disorder)"}
        ])
        self.add_vacc("PERTUSSIS", [
            {"code": "27836007", "term": "Pertussis (disorder)"}
        ])
        self.add_vacc("SHINGLES", [
            {"code": "4740000", "term": "Herpes zoster"}
        ])
        self.add_vacc("PCV13", [
            {"code": "16814004", "term": "Pneumococcal infectious disease"}
        ])
        self.add_vacc("3in1", [
            {"code": "398102009", "term": "Acute poliomyelitis"},
            {"code": "397430003", "term": "Diphtheria caused by Corynebacterium diphtheriae"},
            {"code": "76902006", "term": "Tetanus (disorder)"}])
        self.add_vacc("MENACWY", [
            {"code": "23511006", "term": "Meningococcal infectious disease"}
        ])

        self.add_supplier("SUPPLIER_COVID19_SEARCH", ["COVID19:search"])

    # mock_data = {
    #     "vacc_to_diseases": {
    #         "HPV": json.dumps([{"code": "", "term": ""}])
    #     },
    #     "diseases_to_vacc": {
    #         "": "HPV"
    #     },
    #     "supplier_permissions": {
    #         "": json.dumps([])
    #     }
    # }

    def add_vacc(self, vacc: str, diseases: list[dict]):
        self.mock_data["vacc_to_diseases"][vacc] = json.dumps(diseases)
        self.mock_data["diseases_to_vacc"][":".join(sorted([d["code"] for d in diseases]))] = vacc

    def add_supplier(self, supplier: str, permissions: list[str]):
        self.mock_data["supplier_permissions"][supplier] = json.dumps(permissions)

    def hget(self, key, field):
        return self.mock_data.get(key, {}).get(field, None)

    def hkeys(self, key):
        return self.mock_data.get(key, {}).keys()

def mock_redis(test_case):
    redis_patcher = mock.patch("redis.StrictRedis", return_value=MockRedisClient)
    test_case.addCleanup(redis_patcher.stop)
    redis_patcher.start()
