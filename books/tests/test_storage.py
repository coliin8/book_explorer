from datetime import datetime
from botocore.client import ClientError

from books.models import BookFile
from books.storage import (
    CsvFileExistsError,
    CsvFileValidationError,
    S3UploadFileManager,
)

import pytest


@pytest.fixture
def csv_file_like_object():
    # The above code takes string and converts it into the byte equivalent using encode()
    # so that it can be accepted by the hash function
    with open("books/tests/resources/book-success.csv", "rb") as f:
        yield f


@pytest.fixture
def csv_file_like_object_validation_errors():
    # The above code takes string and converts it into the byte equivalent using encode()
    # so that it can be accepted by the hash function
    with open("books/tests/resources/book-failure.csv", "rb") as f:
        yield f


def test_initialisation(mocker):
    # Setup
    boto3_mock = mocker.patch("books.storage.boto3.client")
    # Actions
    subject = S3UploadFileManager()
    # Assertions
    boto3_mock.return_value.head_bucket.assert_called_once_with(
        Bucket=subject.s3_bucket_name
    )


def test_initialisation_no_bucket(mocker):
    # Setup
    boto3_mock = mocker.patch("books.storage.boto3.client")
    error_response = {"Error": {"Code": "", "Message": ""}}
    boto3_mock.return_value.head_bucket.side_effect = ClientError(
        error_response, "head_bucket"
    )
    # Actions
    subject = S3UploadFileManager()
    # Assertions
    boto3_mock.return_value.head_bucket.assert_called_once_with(
        Bucket=subject.s3_bucket_name
    )
    boto3_mock.return_value.create_bucket.assert_called_once_with(
        Bucket=subject.s3_bucket_name,
        CreateBucketConfiguration={"LocationConstraint": subject.aws_region_name},
    )


def basic_subject_setup(mocker):
    boto3_mock = mocker.patch("books.storage.boto3.client")
    # Actions
    subject = S3UploadFileManager()
    # Assertions
    boto3_mock.return_value.head_bucket.assert_called_once_with(
        Bucket=subject.s3_bucket_name
    )
    return (subject, boto3_mock)


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_upload_success(mocker, csv_file_like_object):
    # Setup
    subject, boto3_mock = basic_subject_setup(mocker)
    # Actions
    db_book_list_obj = subject.upload(csv_file_like_object)
    # Assertions
    s3_file_name = db_book_list_obj.s3_url.split("/")[-1]
    boto3_mock.return_value.upload_fileobj.assert_called_once_with(
        csv_file_like_object, subject.s3_bucket_name, s3_file_name
    )
    assert (
        db_book_list_obj.s3_url
        == f"https://jc1976bucket.s3.eu-west-1.amazonaws.com/{s3_file_name}"
    )
    assert db_book_list_obj.file_name == "books/tests/resources/book-success.csv"
    assert db_book_list_obj.date_uploaded.strftime(
        "%m/%d/%Y"
    ) == datetime.now().strftime("%m/%d/%Y")


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_upload_failure_as_file_already_exists(
    mocker, csv_file_like_object, create_bookfile
):
    # Setup
    subject, boto3_mock = basic_subject_setup(mocker)
    # Actions
    with pytest.raises(CsvFileExistsError) as excinfo:
        subject.upload(csv_file_like_object)
    # Assertions
    assert (
        str(excinfo.value)
        == "books/tests/resources/book-success.csv alreadly been upload to system."
    )


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_upload_failure_as_file_validation_of_fieldnames(
    mocker, csv_file_like_object_validation_errors
):
    # Setup
    subject, boto3_mock = basic_subject_setup(mocker)
    # Actions
    with pytest.raises(CsvFileValidationError) as excinfo:
        subject.upload(csv_file_like_object_validation_errors)
    # Assertions
    assert (
        str(excinfo.value)
        == "CSV Column Headers were ['Book Author', 'Book titlea', 'Date published', 'Publisher name', 'Unique identifer'] and should be ['BOOK AUTHOR', 'BOOK TITLE', 'DATE PUBLISHED', 'PUBLISHER NAME', 'UNIQUE IDENTIFER']!"
    )


def test_retrieve_file(mocker, csv_file_like_object):
    # Setup
    subject, boto3_mock = basic_subject_setup(mocker)
    boto3_mock.return_value.get_object.return_value = {"Body": csv_file_like_object}
    input_book_file = BookFile(s3_url="http://here.com/a.csv")
    # Actions
    output_file = subject.retrieve(input_book_file)
    # Assertions
    boto3_mock.return_value.get_object.assert_called_once_with(
        Bucket=subject.s3_bucket_name, Key=input_book_file.s3_url.split("/")[-1]
    )
    assert output_file == csv_file_like_object
