from unittest.mock import ANY, MagicMock
from botocore.client import ClientError

from books.tasks import check_create_bucket

from books.tests.constants import VALID_CSV_JSON, VALID_CSV_STRING

AWS_REGION = "TEST_REGION"
AWS_BUCKET = "TEST_BUCKET"


def test_check_s3_bucket_exists():
    # Setup
    mock_s3_client = MagicMock()
    # Actions
    subject = check_create_bucket(mock_s3_client, AWS_REGION, AWS_BUCKET)
    # Assertions
    mock_s3_client.head_bucket.assert_called_once_with(Bucket=AWS_BUCKET)


def test_check_s3_bucket_does_not_exist():
    # Setup
    mock_s3_client = MagicMock()
    error_response = {"Error": {"Code": "", "Message": ""}}
    mock_s3_client.head_bucket.side_effect = ClientError(error_response, "head_bucket")
    # Actions
    subject = check_create_bucket(mock_s3_client, AWS_REGION, AWS_BUCKET)
    # Assertions
    mock_s3_client.head_bucket.assert_called_once_with(Bucket=AWS_BUCKET)
    mock_s3_client.create_bucket.assert_called_once_with(
        Bucket=AWS_BUCKET,
        CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
    )


# def test_upload_csv_to_cloud(mocker):
#     # Setup
#     # mock_self = MagicMock()
#     mock_s3_client = mocker.patch("books.tasks.boto3.client")
#     mock_check_bucket = mocker.patch("books.tasks.check_create_bucket")
#     mock_convert_dict_to_csv_helper = mocker.patch(
#         "books.tasks.convert_dict_to_csv_helper", return_value=VALID_CSV_STRING
#     )
#     # Actions
#     upload_csv_to_cloud(AWS_REGION, AWS_BUCKET, "file_name.csv", VALID_CSV_STRING)
#     # Assertions
#     mock_check_bucket.assert_called_once_with(mock_s3_client, AWS_REGION, AWS_BUCKET)
#     mock_convert_dict_to_csv_helper.assert_called_once_with(ANY, VALID_CSV_STRING)
#     mock_s3_client.return_value.put_object(
#         Body=VALID_CSV_STRING, Bucket=AWS_BUCKET, Key="file_name.csv"
#     )
