import csv
from models.samplemodel import SampleModel
from datetime import datetime, timezone

    
def read_csv_to_sample(csv_file):
    samples = []

    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            try:
                # Filter out unwanted fields
                sample = SampleModel(**row)
                samples.append(sample)
            except ValueError as e:
                print(e)

    return samples

if __name__ == "__main__":
    csv_file = 'sample_data/patient_data3.csv'
    samples = read_csv_to_sample(csv_file)

    for sample in samples:
        print(sample)
        