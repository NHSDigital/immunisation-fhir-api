# batch-processor-filter-lambda

## Contributing to this project

You will first need to have the required setup as specified in the root README.

Then, getting set up to contribute to this Lambda is the same for any others. Refer to
the `Setting up a virtual environment with poetry` section in the root README. Assuming 1 and 2 have already been done,
then you will just need to follow steps 3-5 for this specific directory.

Then run:

```
make test
```

to verify your setup.

## Overview

The context of this Lambda function should be understood within the following architecture diagram:
https://nhsd-confluence.digital.nhs.uk/spaces/Vacc/pages/1161762503/Immunisation+FHIR+API+-+Batch+Ingestion+Improvements

The purpose of the batch-processor-filter Lambda function is to ensure that there is only ever one batch file event
processing at any given time for a given combination of `supplier` + `vaccination type`. This is because the order in
which updates are applied is vital; for the same supplier/vacc type combination, there may be changes to the same
patient's vaccination record across 2 different files. Therefore, the order in which they arrive must be preserved.

The Lambda function consumes one event at a time on a per `message group id` (composed of the supplier name + vacc type)
basis from an SQS FIFO queue. At a high-level, the pseudocode is as follows:

- check the Audit Table for any duplicate named files and process accordingly if that is the case
- check the Audit Table if there is already an event processing for the given supplier + vacc type
- if there is not, then update the event's status in the Audit Table and forward to SQS for processing by ECS
- if there is, then throw an error so that the event is returned to the queue and will be tried again later

test
