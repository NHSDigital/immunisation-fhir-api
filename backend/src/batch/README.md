## Overview

The batch processing is a stand-alone package that is responsible for processing the data that we received from an
external source.
This module should be able to deal with the provided CSV files with various quality and shapes.
It is expected that the code in this module will see a lot of changes as the project progresses.
This is why it has its own readme file, and it's recommended to **read it before making any changes to the code**.

## Implementation

The `parser` module parses the pipe separated file and stream the data in a generator. This is important because we
don't want to put the entire content of the source in the memory.
The `processor` module then takes over and start processing data row by row. At every step, we catch all the errors.
Nothing
should stop the processor from processing the entire file.
Before we can send the data to the API, we need to convert it to the `Immunization` resource. This is done in
the `transformer`
module. The `decorator` starts by receiving a base `Immunization` resource and then adds the necessary information to
it. Once we have the resource then `ACTION_FLAG` is checked to see if we need to create, update or delete the resource.
If the processing of a row failed for whatever reason, then we add a row to the report file. `report` module is
responsible
for converting batch error to an error report entry.

### Considerations

Logging is probably the most important part of this module. Because data comes from an external source, and it has
various
quality, we need to log everything. This will help us to debug the issues and also to keep track of the data that we
processed.
Exception handling is also related to logging for exactly the same reason.

#### Resiliency

Creating a resilient system is necessary. You don't want to raise and error if `NHS_LOGIN` is all lowercase. Or, the
order of the column shouldn't matter to your code. Keep it this way when you are adding new code. This is also why
you don't see any type constraints in the code. It's all dictionary and list to keep it simple and flexible for changes.

#### Dealing with errors

There are two types of errors that we need to deal with. In the source code you see them as `handled` and `unhandled`
errors.
`Handled` errors are the ones that we expect to happen, and we can recover from them. You can consider `unhandled`
errors
as bugs. This is why logging is important. In production, you need to have enough information to debug the issue.

#### Validation

Unless you have a specific reason to add validation in the processor, it's recommended to keep the validation in the
API side.

### Error recovery

If a record fails to process, then you need to consider a recovery process. If the failure is due to a bug, and you
should
have been sending this data, then the question is how would you recover from that? We have already missed the
opportunity to
process that row, so it's gone. Right now, there is really no solution for this in the batch itself.
One way to deal with this is to make the entire process idempotent. So in cases like this, after fixing the bug, you can
upload the file again.
