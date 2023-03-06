import pytest

from datetime import datetime
from books.validators import BookListCsvValidator


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_validate_success(csv_file_like_object):
    # Actions
    subject = BookListCsvValidator()
    result_action = subject.validate(csv_file_like_object)
    # Assertions
    assert result_action.is_success
    db_obj = result_action.result_object
    assert "https://jc1976bucket.s3.eu-west-1.amazonaws.com/" in db_obj.s3_url
    assert db_obj.file_name == "books/tests/resources/book-success.csv"
    assert db_obj.date_uploaded.strftime("%m/%d/%Y") == datetime.now().strftime(
        "%m/%d/%Y"
    )


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_validate_duplicate(csv_file_like_object, create_bookfile):
    # Actions
    subject = BookListCsvValidator()
    result_action = subject.validate(csv_file_like_object)
    # Assertions
    assert (
        result_action.message
        == "Failed to upload books/tests/resources/book-success.csv due to validation - File already been upload to system."
    )


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_validate_failure(csv_file_like_object_validation_errors):
    # Actions
    subject = BookListCsvValidator()
    result_action = subject.validate(csv_file_like_object_validation_errors)
    # Assertions
    assert not result_action.is_success
    assert (
        result_action.message
        == "Failed to upload books/tests/resources/book-failure.csv due to validation - CSV Column Headers were ['Book Author', 'Book titlea', 'Date published', 'Publisher name', 'Unique identifer'] and should be ['BOOK AUTHOR', 'BOOK TITLE', 'DATE PUBLISHED', 'PUBLISHER NAME', 'UNIQUE IDENTIFER']!."
    )
    assert not result_action.result_object


# def test_retrieve_success(mocker, csv_file_like_object):
#     # Setup
#     boto3_mock = mocker.patch("books.storage.aws.boto3.client")
#     boto3_mock.return_value.get_object.return_value = {"Body": csv_file_like_object}
#     input_book_file = BookFile(s3_url="http://here.com/a.csv")
#     # Actions
#     subject = BookListCsvValidator()
#     output_file = subject.retrieve(input_book_file)
#     # Assertions
#     boto3_mock.return_value.get_object.assert_called_once_with(
#         Bucket=subject.s3_bucket_name, Key=input_book_file.s3_url.split("/")[-1]
#     )
#     assert output_file == csv_file_like_object


# def test_retrieve_failure(mocker, csv_file_like_object):
#     # Setup
#     boto3_mock = mocker.patch("books.storage.aws.boto3.client")
#     error_response = {"Error": {"Code": "", "Message": ""}}
#     boto3_mock.return_value.get_object.side_effect = ClientError(
#         error_response, "get_object"
#     )
#     input_book_file = BookFile(s3_url="http://here.com/a.csv")
#     # Actions
#     subject = BookListCsvValidator()
#     with pytest.raises(ClientError) as excinfo:
#         subject.retrieve(input_book_file)
#     # Assertions
#     assert (
#         str(excinfo.value)
#         == "An error occurred () when calling the get_object operation: "
#     )
