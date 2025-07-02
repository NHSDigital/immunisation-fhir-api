import json

MOCK_REDIS_D2V_RESPONSE = json.dumps({
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
})

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
last = None
def get_data(name):
    # extract name of calling unit test and print to console
    import inspect
    # static variable to keep track of last printed message
    global last
    # get the name of the calling unit test
    # this is useful for debugging and understanding which test is calling this mock
    # function, especially when multiple tests are using the same mock
    test_name = None
    for frame_info in inspect.stack():
        if frame_info.function.startswith("test_"):
            test_name = frame_info.function
            # Optionally, get the class name if available
            test_self = frame_info.frame.f_locals.get("self", None)
            msg = ''
            if test_self:
                test_class = type(test_self).__name__
                msg = f"Mocking redis call for: {test_class} - {test_name}"
            else:
                msg = f"Mocking redis call for: {test_name}"

            if msg != last:
                print(msg)
                last = msg

            break
    else:
        print("Mocking redis call: test function not found in stack.")

    
    
    
    if name == "diseases_to_vacc":
        return MOCK_REDIS_D2V_RESPONSE
    elif name == "vacc_to_diseases":
        return MOCK_REDIS_V2D_RESPONSE
    return {}

def mock_redis_hget(name, key):
    ret = get_data(name)
    if key in ret:
        print(f"Mocking redis hget({name},{key}): {ret[key]}")
        return ret[key]
    
    print(f"Mocking redis hget({name},{key}): None")
    return {}

def mock_redis_hkeys(name):
    ret = get_data(name)
    # return all keys
    if isinstance(ret, dict) and ret:
        return list(ret.keys())
    return []
