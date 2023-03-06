from typing import Dict, List
import io

from celery import shared_task, Task
import boto3
from botocore.exceptions import ClientError
import requests

from books.helpers import convert_dict_to_csv_helper, convert_csv_to_dict_helper


class BaseTaskWithRetry(Task):
    autoretry_for = (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
    retry_kwargs = {"max_retries": 25}
    retry_backoff = 5
    retry_jitter = (True,)


@shared_task(bind=True, base=BaseTaskWithRetry)
def process_notification_task(self, s3_url: str):
    """Simple task to send 3_url to notification to Postman

    Args:
        s3_url (str): S3 Url of new File created in S3
    """
    requests.post(
        "https://postman-echo.com/post",
        data=s3_url.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )


def check_create_bucket(s3_client, region_name: str, bucket_name: str):
    """Check if bucket exists, if it does then create it"""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region_name},
        )


@shared_task(bind=True)
def upload_csv_to_s3_task(
    self,
    region_name: str,
    bucket_name: str,
    file_name: str,
    csv_json: Dict[str, List[Dict[str, str]]],
):
    """Task to upload CSV file to S3 using boto3 library.

    Args:
        region (str): AWS Region
        bucket_name (str): AWS S3 Bucket Name
        file_name (str): Name of file to be addedto S3 bucket
        csv_json (Dict[str, List[Dict[str, str]]]): Json containing CSV rows as Json.

    Raises:
        ClientError: Raise Boto3 Client exception when it is not possible to upload file.
    """
    s3_client = boto3.client("s3")
    check_create_bucket(s3_client, region_name, bucket_name)
    with io.StringIO() as f:
        body = convert_dict_to_csv_helper(f, csv_json)
        try:
            s3_client.put_object(Body=body, Bucket=bucket_name, Key=file_name)
        except ClientError as e:
            # Check for specific things that will mean a complete failure.
            # Just added as example.
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                raise e
            self.retry()


@shared_task()
def retrieve_json_from_s3_task(
    bucket_name: str,
    file_name: str,
) -> Dict:
    s3_client = boto3.client("s3")
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        return convert_csv_to_dict_helper(obj["Body"])
    except ClientError as e:
        # Check for specific things that will mean a complete failure.
        raise e
