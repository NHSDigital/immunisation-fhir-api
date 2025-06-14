"Upload the content from a config file in S3 to ElastiCache (Redis)"

from clients import s3_client
from clients import logger


class S3Reader:

    @staticmethod
    def read(bucket_name, file_key):
        try:
            s3_file = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            return s3_file["Body"].read().decode("utf-8")

        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Error reading S3 file '%s' from bucket '%s'", file_key, bucket_name)
            raise error
