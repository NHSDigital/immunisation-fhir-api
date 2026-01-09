from utilities.error_constants import ERROR_MAP


def validate_bus_ack_file_for_successful_records(context, file_rows) -> bool:
    if not file_rows:
        print("No rows found in BUS ACK file for successful records")
        return True
    else:
        success_mask = (
            ~context.vaccine_df["UNIQUE_ID"].str.startswith("Fail-", na=False) &
            (context.vaccine_df["UNIQUE_ID"].str.strip() != "")
        )

        success_df = context.vaccine_df[success_mask]

        valid_ids = set(success_df["UNIQUE_ID"].astype(str) + "^" + success_df["UNIQUE_ID_URI"].astype(str))
        
        file_ids = set(file_rows["LOCAL_ID"].astype(str))

        intersection = valid_ids & file_ids

        if intersection:
            print(f"Unexpected valid IDs found in BUS ACK file: {intersection}")
            return False
        else:
            print("No successful records present in BUS ACK file — validation passed")
            return True   


def validate_inf_ack_file(context, success: bool = True) -> bool:
    content = context.fileContent
    lines = content.strip().split("\n")
    header = lines[0].split("|")
    row = lines[1].split("|")
    expected_columns = 12

    if len(header) != expected_columns:
        print(f"Header column count mismatch: expected {expected_columns}, got {len(header)}")
        return False
    
    row_valid = True  # Reset for each row

    if len(row) != expected_columns:
        print(f"Row {i}: column count mismatch ({len(row)} fields)")
        overall_valid = False
        return False

    header_response_code = row[1]
    issue_severity = row[2]
    issue_code = row[3]
    response_code = row[6]
    response_display = row[7]
    message_delivery = row[11]
    
    if success:
        expected_message_delivery = "True"
        excepted_header_response_code = "Success"
        excepted_issue_severity = "Information"
        excepted_issue_code = "OK"  
        excepted_response_code = "20013"
        expected_response_display = "Success"
    else:
        expected_message_delivery = "False"
        excepted_header_response_code = "Failure"
        excepted_issue_severity = "Fatal"
        excepted_issue_code = "Fatal Error"  
        excepted_response_code = "10002"
        expected_response_display = "Infrastructure Level Response Value - Processing Error"

    if header_response_code != excepted_header_response_code:
        print(f"HEADER_RESPONSE_CODE is not {excepted_header_response_code}")
        row_valid = False
    if issue_severity != excepted_issue_severity:
        print(f"ISSUE_SEVERITY is not {excepted_issue_severity}")
        row_valid = False
    if issue_code != excepted_issue_code:
        print(f"ISSUE_CODE is not {excepted_issue_code}")
        row_valid = False
    if response_code != excepted_response_code:
        print(f"RESPONSE_CODE is not {excepted_response_code}")
        row_valid = False
    if response_display != expected_response_display:
        print(f"RESPONSE_DISPLAY is not {expected_response_display}")
        row_valid = False
    if message_delivery != expected_message_delivery:
        print(f"MESSAGE_DELIVERY is not {expected_message_delivery}")
        row_valid = False
    
    return row_valid

def normalize_for_lookup(id_str: str) -> str:
    parts = str(id_str).split("^")
    prefix = parts[0].strip() if len(parts) > 0 else ""
    suffix = parts[1].strip() if len(parts) > 1 else ""
    normalized_prefix = "" if prefix in ["", "nan"] else prefix
    normalized_suffix = "" if suffix in ["", "nan"] else suffix
    return f"{normalized_prefix}^{normalized_suffix}"

def validate_bus_ack_file_for_error(context, file_rows) -> bool:
    
    if not file_rows:
        print("No rows found in BUS ACK file for failed records")
        return False

    fail_mask = (
        context.vaccine_df["UNIQUE_ID"].str.startswith("Fail-", na=False) | (context.vaccine_df["UNIQUE_ID"].str.strip() == "")
     )

    fail_df = context.vaccine_df[fail_mask]

    valid_ids = set(fail_df["UNIQUE_ID"].astype(str) + "^" + fail_df["UNIQUE_ID_URI"].astype(str))

    overall_valid = True

    for valid_id in valid_ids:
        normalized_id = normalize_for_lookup(valid_id)
        row_data_list = file_rows.get(normalized_id)

        if not row_data_list:
            print(f"Valid ID '{valid_id}' not found in file")
            overall_valid = False
            continue
        
        for row_data in row_data_list:
            i = row_data["row"]
            fields = row_data["fields"]
            row_valid = True

            header_response_code = fields[1]
            issue_severity = fields[2]
            issue_code = fields[3]
            response_code = fields[6]
            response_display = fields[7]
            local_id = fields[10]
            imms_id = fields[11]
            operation_outcome = fields[12]
            message_delivery = fields[13]

        
            if header_response_code != "Fatal Error":
                print(f"Row {i}: HEADER_RESPONSE_CODE is not 'Fatal Error'")
                row_valid = False
            if issue_severity != "Fatal":
                print(f"Row {i}: ISSUE_SEVERITY is not 'Fatal'")
                row_valid = False
            if issue_code != "Fatal Error":
                print(f"Row {i}: ISSUE_CODE is not 'Fatal Error'")
                row_valid = False
            if response_code != "30002":
                print(f"Row {i}: RESPONSE_CODE is not '30002'")
                row_valid = False
            if response_display != "Business Level Response Value - Processing Error":
                print(f"Row {i}: RESPONSE_DISPLAY is not expected value")
                row_valid = False
            if imms_id:
                print(f"Row {i}: IMMS_ID is populated but should be null")
                row_valid = False
            if message_delivery != "False":
                print(f"Row {i}: MESSAGE_DELIVERY is not 'False'")
                row_valid = False

            try:
                valid_id_df = context.vaccine_df.loc[i-2]
                prefix = str(valid_id_df["UNIQUE_ID"]).strip()

                if prefix in ["", " ","nan"]:
                    expected_error = valid_id_df["PERSON_SURNAME"] if not valid_id_df.empty else "no_valid_surname"

                else:
                    split_parts = prefix.split("-")
                    expected_error = split_parts[2] if len(split_parts) > 2 else "invalid_prefix_format"

                expected_diagnostic = ERROR_MAP.get(expected_error, {}).get("diagnostics")

                if operation_outcome != expected_diagnostic:
                    print(f"Row {i}: operation_outcome does not match expected diagnostics '{expected_diagnostic}' for '{expected_error}' but got '{operation_outcome}'")
                    row_valid = False

            except Exception as e:
                print(f"Row {i}: error extracting expected diagnostics from local_id '{valid_id}': {e}")
                row_valid = False

            overall_valid = overall_valid and row_valid

    return overall_valid

def read_and_validate_bus_ack_file_content(
    context, 
    by_local_id: bool = True, 
    by_row_number: bool = False
) -> dict:

    # Prevent invalid combinations
    if by_local_id and by_row_number:
        raise ValueError("Choose only one mode: by_local_id OR by_row_number")

    content = context.fileContent.strip()
    lines = content.split("\n")

    expected_header = [
        "MESSAGE_HEADER_ID",
        "HEADER_RESPONSE_CODE",
        "ISSUE_SEVERITY",
        "ISSUE_CODE",
        "ISSUE_DETAILS_CODE",
        "RESPONSE_TYPE",
        "RESPONSE_CODE",
        "RESPONSE_DISPLAY",
        "RECEIVED_TIME",
        "MAILBOX_FROM",
        "LOCAL_ID",
        "IMMS_ID",
        "OPERATION_OUTCOME",
        "MESSAGE_DELIVERY",
    ]

    if not lines:
        print("File is empty")
        return {}

    header = lines[0].split("|")
    if header != expected_header:
        print("Header mismatch")
        return {}

    file_rows = {}

    if by_local_id:
        for i, line in enumerate(lines[1:], start=2):
            fields = line.split("|")
            local_id = normalize_for_lookup(fields[10])

            file_rows.setdefault(local_id, []).append(
                {
                    "row": i,
                    "fields": fields,
                    "original_local_id": fields[10],
                }
            )
        return file_rows

    if by_row_number:
        for i, line in enumerate(lines[1:], start=2):
            fields = line.split("|")

            file_rows[i] = [
                {
                    "row": i,
                    "fields": fields,
                    "original_local_id": fields[10],
                }
            ]
        return file_rows

    raise ValueError("You must select either by_local_id=True or by_row_number=True")