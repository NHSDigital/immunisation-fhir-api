import re
import sys


def extract_failed_tests(log_file):
    """Extract failed test names from the log file.."""
    failed_tests = []
    print(f"log_file:{log_file}")
    with open(log_file, "r") as f:
        for line in f:
            match = re.search(r"FAIL: (\S+)", line)
            if match:
                failed_tests.append(match.group(1))
    return failed_tests


if __name__ == "__main__":
    log_file = sys.argv[1]  # Get the log file path from arguments
    failed_tests = extract_failed_tests(log_file)

    # Print space-separated test names for Bash script
    print(" ".join(failed_tests))
