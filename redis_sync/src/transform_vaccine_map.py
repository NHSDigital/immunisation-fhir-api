'''
for json structure
{
    "disease": {"d1": {}, "d2": {}, "d3": {}},
    "vaccine": {"v1": {"diseases": ["d1"]}, "v2": {"diseases": ["d1", "d3"]}}
}
modify the disease key to hold 1 to many relationship with vaccine key

'''


def transform_vaccine_map(data):
    # Transform the vaccine map data as needed

    vaccines = data["vaccine"]
    diseases = data["disease"]

    # vaccines has a 1 to many with disease. Disease needs to have a reciprocal relationship
    for vaccine_id, vaccine_data in vaccines.items():
        for disease_id in vaccine_data["diseases"]:
            if "vaccines" not in diseases[disease_id]:
                diseases[disease_id]["vaccines"] = []
            diseases[disease_id]["vaccines"].append(vaccine_id)
    return data
