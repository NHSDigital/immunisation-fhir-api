import unittest
from unittest.mock import Mock, patch

from mesh_backlog_metric import publish_mesh_object_event_metric


class TestMeshBacklogMetric(unittest.TestCase):
    @patch("mesh_backlog_metric.boto3.client")
    def test_publish_mesh_backlog_metric(self, mock_boto_client):
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch

        with patch("mesh_backlog_metric.METRIC_NAMESPACE", "imms-preprod-MeshProcessorObjectCount"):
            publish_mesh_object_event_metric("TestMetric", 5, bucket="test-bucket")

        mock_boto_client.assert_called_once_with("cloudwatch")
        mock_cloudwatch.put_metric_data.assert_called_once_with(
            Namespace="imms-preprod-MeshProcessorObjectCount",
            MetricData=[
                {
                    "MetricName": "TestMetric",
                    "Dimensions": [{"Name": "Bucket", "Value": "test-bucket"}],
                    "Unit": "Count",
                    "Value": 5,
                }
            ],
        )

    @patch("mesh_backlog_metric.boto3.client")
    def test_publish_mesh_backlog_metric_does_not_raise(self, mock_boto_client):
        mock_cloudwatch = Mock()
        mock_cloudwatch.put_metric_data.side_effect = Exception("error")
        mock_boto_client.return_value = mock_cloudwatch

        with patch("mesh_backlog_metric.METRIC_NAMESPACE", "imms-preprod-MeshProcessorObjectCount"):
            publish_mesh_object_event_metric("TestMetric", 5, bucket="test-bucket")
