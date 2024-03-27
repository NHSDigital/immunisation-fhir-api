import json
import sys

"""This module is just a helper script for a developer and not part of the application.
You can use it to convert a dat file into json for each row"""

# The number of rows to print
LIMIT = 2


def dat_to_json(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Get the keys from the first line
    keys = lines[0].strip().split('|')

    count = 0
    for line in lines[1:]:
        if count >= LIMIT:
            break
        count += 1

        values = line.strip().split('|')
        values = [value.strip('"') for value in values]  # Remove the double quotes from the values
        json_obj = dict(zip(keys, values))
        print(json.dumps(json_obj, indent=4))


def main():
    if len(sys.argv) != 2:
        print("Usage: python dat_helper_script.py <path_to_dat_file>")
        return

    dat_file_path = sys.argv[1]
    dat_to_json(dat_file_path)


if __name__ == '__main__':
    main()
