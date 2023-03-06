from datetime import datetime
import pytest

from books.models import BookFile

# pytest_plugins = ("celery.contrib.pytest",)


# @pytest.fixture(scope="session")
# def celery_config():
#     return {"broker_url": "memory://", "result_backend": "rpc://"}


@pytest.fixture
def create_bookfile():
    book_file = BookFile(
        file_name="books/tests/resources/book-success.csv",
        s3_url="https://jc1976bucket.s3.eu-west-1.amazonaws.com/123456789.csv",
        date_uploaded=datetime.now(),
        md5_checksum="3ec0c7f80abe671f09c2ecb0a7bb12ff",
    )
    book_file.save()
    return book_file


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
