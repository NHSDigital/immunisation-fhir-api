class S3EventRecord:
    """
    S3 Event Parsing Utilities
    This module defines helper classes for extracting relevant information from
    AWS S3 event records, such as the bucket name and object key.
    - `S3EventRecord` provides access to individual record fields.
    - `S3Event` wraps the event and extracts a list of `S3EventRecord` objects.
    """
    def __init__(self, s3_record):
        self.s3_record = s3_record

    def get_bucket_name(self):
        bucket = self.s3_record['bucket']
        return bucket.get('name')

    def get_object_key(self):
        ret = self.s3_record['object']['key']
        return ret


class S3Event:
    def __init__(self, event):
        self.event = event

    def get_s3_records(self):
        # return a list of S3EventRecord objects - stripping out the s3 key
        return [S3EventRecord(record['s3']) for record in self.event['Records']]
