from common.clients import s3_client, logger


class S3Reader:

    """
    Fetch the file from S3 using the specified bucket and key.
    The file is expected to be a UTF-8 encoded text file (e.g., JSON or plain text).
    We read the file content from the response body and decode it into a string.
    This string can then be passed to json.loads() or other parsers as needed.
    """

    @staticmethod
    def read(bucket_name, file_key):
        try:
            print(f"SAW: Reading S3 file '{file_key}' from bucket '{bucket_name}'")
            s3_file = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            print(f"SAW: Successfully read S3 file '{file_key}' from bucket '{bucket_name}'")
            print(f"SAW: S3 file content: {s3_file}")
            return s3_file["Body"].read().decode("utf-8")

        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Error reading S3 file '%s' from bucket '%s'", file_key, bucket_name)
            raise error
