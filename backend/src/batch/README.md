## Overview
The batch processing module is a stand-alone module that is responsible for processing the data in the database. It is a command line application that can be run on a schedule or on demand. The module is written in Python and uses the SQLAlchemy library to interact with the database. The module is designed to be extensible and can be easily modified to add new processing tasks.
This module deals with the provided CSV files with various quality and shapes. It is expected that the code in this
module will see a lot of changes as the project progresses. This is why it has its own readme file and it's recommended 
to **read it before making any changes to the code**.

batch-file -> s3 -> event -> task -> report(s3)
