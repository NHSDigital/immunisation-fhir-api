# record-processor project

## Overview

The Record Processor component is a core part of the batch processing system. The functionality is as follows:

- receive a batch job event from EventBridge pipes. The job will contain the filename, so that the batch .csv/.dat file
  can be retrieved, along with other metadata such as the supplier name and their permissions.
- perform high-level validation e.g. marking a job as processed if the file is empty or failed if the supplier does not
  have permissions to interact with the requested vaccination type.
- reads the batch source file and processes the content row by row.
- for each of the rows, it validates whether the supplier can perform the given operation i.e. CREATE, UPDATE or DELETE
  and also checks for critical information such as the unique ID.
- finally, if such checks pass, the flat CSV structure will be converted to an R4 Immunization FHIR JSON payload. The
  mapping is performed in `utils_for_fhir_conversion.py`.
- the content is sent to Kinesis for further downstream processing where the requested operations will be performed on
  the IEDS table.

For more context, refer to the [Architecture Overview](https://nhsd-confluence.digital.nhs.uk/spaces/Vacc/pages/1035417049/Immunisation+FHIR+API+-+Solution+Architecture) in Confluence.

Finally, it is worth noting that this package is **not** deployed as a Lambda function. As the file processing can take
some time for particularly large extracts, this is run in AWS ECS.

## Set up

Simply follow the instructions from the root README on _Setting up a virtual environment with poetry_.
As is the case for developing with any of the Python projects, it is easiest to create a `.env` file, a `.envrc` file,
and then install the poetry dependencies using `poetry install --no-root`.
