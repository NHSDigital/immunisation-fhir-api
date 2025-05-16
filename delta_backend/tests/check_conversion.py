import json
import csv
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from delta_converter import Converter


# Sample FHIR Immunization resource (minimal test data)
fhir_sample = os.path.join(os.path.dirname(__file__),"sample_data", "fhir_sample.json")


with open(fhir_sample, "r", encoding="utf-8") as f:
    json_data = json.load(f)

# Run the converter
converter = Converter(json_data)
result = converter.run_conversion()

# Absolute path to /delta_backend
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# Full paths to files
json_path = os.path.join(output_dir, "output.json")
csv_path = os.path.join(output_dir, "output.csv")

# Output result

print(json.dumps(result, indent=2))

with open(json_path, "w") as f:
    json.dump(result, f, indent=2)

# Convert JSON list of dicts to CSV
if result:
    keys = result.keys()
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerow(result)

print("CSV saved to:", csv_path)
print("JSON saved to:", json_path)
