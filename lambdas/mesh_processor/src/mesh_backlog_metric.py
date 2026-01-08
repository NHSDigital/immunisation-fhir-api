import os

import boto3

from common.clients import logger

METRIC_NAMESPACE = os.getenv("METRIC_NAMESPACE")


def publish_mesh_object_event_metric(metric_name: str, objects_processed: int, bucket: str) -> None:
    try:
        cloudwatch = boto3.client("cloudwatch")
        cloudwatch.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": [{"Name": "Bucket", "Value": bucket}],
                    "Unit": "Count",
                    "Value": objects_processed,
                }
            ],
        )
    except Exception:
        logger.exception("Failed to publish CloudWatch metric")
