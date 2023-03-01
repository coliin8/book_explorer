from datetime import datetime
import pytest

from books.models import BookFile


@pytest.fixture
def create_bookfile():
    book_file = BookFile(
        file_name="books/tests/resources/example.csv",
        s3_url="https://jc1976bucket.s3.eu-west-1.amazonaws.com/123456789.csv",
        date_uploaded=datetime.now(),
        md5_checksum="3ec0c7f80abe671f09c2ecb0a7bb12ff",
    )
    book_file.save()
    return book_file
