import boto3
import io
import json
from abc import abstractmethod, ABC
from dataclasses import dataclass


class S3Upload(ABC):
    @abstractmethod
    def add_data(self, data: bytes):
        pass

    @abstractmethod
    def close(self):
        pass


class S3UploadStream(S3Upload):
    def __init__(self, bucket, key):
        self.s3_client = boto3.client('s3')
        self.bucket = bucket
        self.key = key
        self.multipart_upload = self.s3_client.create_multipart_upload(Bucket=self.bucket, Key=self.key)
        self.parts = []
        self.part_number = 1

    def add_data(self, data: bytes):
        try:
            part = self.s3_client.upload_part(
                Body=data,
                Bucket=self.bucket,
                Key=self.key,
                UploadId=self.multipart_upload['UploadId'],
                PartNumber=self.part_number
            )
            self.parts.append({'PartNumber': self.part_number, 'ETag': part['ETag']})
            self.part_number += 1
        except Exception as e:
            print(f"An error occurred while uploading part {self.part_number}: {e}")
            # Handle the error (e.g., retry the upload)

    def close(self):
        try:
            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=self.key,
                UploadId=self.multipart_upload['UploadId'],
                MultipartUpload={'Parts': self.parts}
            )
        except Exception as e:
            print(f"An error occurred while completing the multipart upload: {e}")
            # Handle the error (e.g., retry the upload)


class S3FixedBufferStream(S3Upload):
    def __init__(self, s3_client, bucket, key):
        self.s3_client = s3_client
        self.bucket = bucket
        self.key = key
        self.stream = io.BytesIO()

    def add_data(self, data: bytes):
        self.stream.write(data)
        self.stream.write(b'')

    def close(self):
        self.stream.seek(0)
        self.s3_client.upload_fileobj(self.stream, self.bucket, self.key)
        self.stream.close()


@dataclass
class ReportEntry:
    """the data you need inorder to map our error to report error"""
    message: str


class ReportEntryTransformer:
    @staticmethod
    def transform_error(entry: ReportEntry) -> str:
        return json.dumps(entry.__dict__)


class ReportGenerator:
    def __init__(self, transformer: ReportEntryTransformer, s3_stream: S3Upload):
        self.transformer = transformer
        self.s3_stream = s3_stream

    def add_error(self, entry: ReportEntry):
        entry_str = self.transformer.transform_error(entry)
        self.s3_stream.add_data(entry_str.encode())

    def close(self):
        self.s3_stream.close()
