import csv
from models.ImmunizationModel import ImmunizationModel


def read_csv_to_sample(csv_file):
    immunizations = []

    with open(csv_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:

            try:
                # Filter out unwanted fields
                imms = ImmunizationModel(**row)
                immunizations.append(imms)
            except ValueError as e:
                print(e)

    return immunizations


if __name__ == "__main__":
    csv_file = "sample_data/patient_data3.csv"
    immunizations = read_csv_to_sample(csv_file)

    for imms in immunizations:
        print(imms)
