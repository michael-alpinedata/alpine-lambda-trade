import os
import pytest
from moto import mock_aws
import boto3

@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-north-1"
    os.environ["S3_BUCKET_NAME"] = "alt-raw-data"
    os.environ["SQS_QUEUE_NAME"] = "alt-ticker-queue.fifo"
    os.environ["SYMBOLS"] = "BTC/USDT"
    if "AWS_ENDPOINT_URL" in os.environ:
        del os.environ["AWS_ENDPOINT_URL"]

@pytest.fixture(scope="function")
def s3_client():
    with mock_aws():
        client = boto3.client("s3", region_name="eu-north-1")
        client.create_bucket(
            Bucket="alt-raw-data",
            CreateBucketConfiguration={"LocationConstraint": "eu-north-1"},
        )
        yield client

@pytest.fixture(scope="function")
def sqs_client():
    with mock_aws():
        client = boto3.client("sqs", region_name="eu-north-1")
        client.create_queue(
            QueueName="alt-ticker-queue.fifo",
            Attributes={'FifoQueue': 'true'}
        )
        yield client
