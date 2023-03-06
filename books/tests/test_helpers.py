from io import StringIO
import pytest

from . import StubAsyncResult

from books.helpers import (
    check_csv_upload_state_helper,
    convert_csv_to_dict_helper,
    convert_dict_to_csv_helper,
)
from books.tests.constants import VALID_CSV_JSON, VALID_CSV_STRING


@pytest.mark.django_db
def test_check_csv_upload_state_helper_success(create_bookfile):
    # Setup
    stub_async_result = StubAsyncResult("fd9h9gudgys8", "SUCCESS", None)
    # Actions
    result = check_csv_upload_state_helper(stub_async_result, 1)
    # Assertion
    assert result.is_success
    assert not result.message
    assert not result.result_object


@pytest.mark.django_db
def test_check_csv_upload_state_helper_pending(mocker, create_bookfile):
    # Setup
    stub_async_result = StubAsyncResult("fd9h9gudgys8", "PENDING", None)
    # Actions
    result = check_csv_upload_state_helper(stub_async_result, 1)
    # Assertion
    assert result.is_success
    assert result.message == "PENDING"
    assert not result.result_object


@pytest.mark.django_db
def test_check_csv_upload_state_helper_failure(mocker, create_bookfile):
    # Setup
    stub_async_result = StubAsyncResult(
        "fd9h9gudgys8", "FAILURE", Exception("Async Task Failure")
    )
    # Actions
    result = check_csv_upload_state_helper(stub_async_result, 1)
    # Assertion
    assert not result.is_success
    assert result.message == "Async Task Failure"
    assert not result.result_object


def test_convert_csv_to_dict_helper_success(csv_file_like_object):
    # Actions
    result = convert_csv_to_dict_helper(csv_file_like_object)
    # Assertion
    assert result == VALID_CSV_JSON


def test_convert_dict_to_csv_helper_success():
    # Actions
    with StringIO() as io:
        result = convert_dict_to_csv_helper(io, VALID_CSV_JSON)
    # Assertion
    assert result == VALID_CSV_STRING
