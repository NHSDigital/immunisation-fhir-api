from unittest import TestCase
from unittest.mock import patch, MagicMock
from src.converter import lambda_handler, ensure_dat_extension


class TestLambdaHandler(TestCase):

    @patch('boto3.client')
    @patch('os.getenv')
    def test_lambda_handler_success(self, mock_getenv, mock_boto_client):
        # Mock environment variable
        mock_getenv.return_value = "destination-bucket"

        # Mock boto3 S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.return_value = {
            'Metadata': {'mex-filename': '20250320121710483244_2DB240.txt'}
        }

        # Define the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "source-bucket"},
                        "object": {"key": "20250320121710483244_2DB240.dat"}
                    }
                }
            ]
        }
        context = {}

        # Call the lambda_handler function
        response = lambda_handler(event, context)

        # Assertions
        mock_s3.get_object.assert_called_with(Bucket="source-bucket", Key="20250320121710483244_2DB240.dat")
        mock_s3.copy_object.assert_called_with(
            CopySource={'Bucket': "source-bucket", 'Key': "20250320121710483244_2DB240.dat"},
            Bucket="destination-bucket",
            Key="20250320121710483244_2DB240.dat"
        )
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['body'], 'Files converted and uploaded successfully!')

    def test_ensure_dat_extension_with_other_extension(self):
        # Test case where file has an extension other than 'dat'
        result = ensure_dat_extension("COVID19_Vaccinations_v5_YGM41_20240927T13005921.txt")
        self.assertEqual(result, "COVID19_Vaccinations_v5_YGM41_20240927T13005921.dat")

    def test_ensure_dat_extension_with_dat_extension(self):
        # Test case where file already has a 'dat' extension
        result = ensure_dat_extension("COVID19_Vaccinations_v5_YGM41_20240927T13005921.dat")
        self.assertEqual(result, "COVID19_Vaccinations_v5_YGM41_20240927T13005921.dat")

    def test_ensure_dat_extension_without_extension(self):
        # Test case where file has no extension
        result = ensure_dat_extension("COVID19_Vaccinations_v5_YGM41_20240927T13005921")
        self.assertEqual(result, "COVID19_Vaccinations_v5_YGM41_20240927T13005921.dat")
