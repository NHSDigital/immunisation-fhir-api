import json
MOCK_REDIS_D2V_RESPONSE = {
    "4740000": "SHINGLES",
    "6142004": "FLU",
    "16814004": "PCV13",
    "23511006": "MENACWY",
    "27836007": "PERTUSSIS",
    "55735004": "RSV",
    "240532009": "HPV",
    "840539006": "COVID19",
    "14189004:36653000:36989005": "MMR",
    "14189004:36653000:36989005:38907003": "MMRV",
    "397430003:398102009:76902006": "3in1"
}

MOCK_REDIS_V2D_RESPONSE = {
    "PERTUSSIS": "[{\"code\": \"27836007\", \"term\": \"Pertussis (disorder)\"}]",
    "RSV": "[{\"code\": \"55735004\", \"term\": \"Respiratory syncytial virus infection (disorder)\"}]",
    "3in1": "[{\"code\": \"398102009\", \"term\": \"Acute poliomyelitis\"}, {\"code\": \"397430003\", \"term\": \"Diphtheria caused by Corynebacterium diphtheriae\"}, {\"code\": \"76902006\", \"term\": \"Tetanus (disorder)\"}]",
    "MMR": "[{\"code\": \"14189004\", \"term\": \"Measles (disorder)\"}, {\"code\": \"36989005\", \"term\": \"Mumps (disorder)\"}, {\"code\": \"36653000\", \"term\": \"Rubella (disorder)\"}]",
    "HPV": "[{\"code\": \"240532009\", \"term\": \"Human papillomavirus infection\"}]",
    "MMRV": "[{\"code\": \"14189004\", \"term\": \"Measles (disorder)\"}, {\"code\": \"36989005\", \"term\": \"Mumps (disorder)\"}, {\"code\": \"36653000\", \"term\": \"Rubella (disorder)\"}, {\"code\": \"38907003\", \"term\": \"Varicella (disorder)\"}]",
    "PCV13": "[{\"code\": \"16814004\", \"term\": \"Pneumococcal infectious disease\"}]",
    "SHINGLES": "[{\"code\": \"4740000\", \"term\": \"Herpes zoster\"}]",
    "COVID19": "[{\"code\": \"840539006\", \"term\": \"Disease caused by severe acute respiratory syndrome coronavirus 2\"}]",
    "FLU": "[{\"code\": \"6142004\", \"term\": \"Influenza caused by seasonal influenza virus (disorder)\"}]",
    "MENACWY": "[{\"code\": \"23511006\", \"term\": \"Meningococcal infectious disease\"}]"
}


def get_data(name):
    if name == "diseases_to_vacc":
        return MOCK_REDIS_D2V_RESPONSE
    elif name == "vacc_to_diseases":
        return MOCK_REDIS_V2D_RESPONSE
    return {}

def fake_hget(name, key):
    ret = get_data(name)
    if key in ret:
        return ret[key]
    return {}

def fake_hkeys(name):
    ret = get_data(name)
    # return all keys
    if ret != {}:
        return list(ret.keys())
    return []
