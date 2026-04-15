#!/usr/bin/env python3
"""
set_version.py

Reads an openapi spec on stdin and adds the calculated version to it,
then prints it on stdout.
"""

import json
import sys

from calculate_version import calculate_version


def main():
    """Main entrypoint"""
    data = json.loads(sys.stdin.read())
    data["info"]["version"] = str(calculate_version())
    sys.stdout.write(json.dumps(data, indent=2))
    sys.stdout.close()


if __name__ == "__main__":
    main()
