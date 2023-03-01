from datetime import datetime

import pytest

from books.models import BookFile


@pytest.mark.freeze_time("2023-02-07")
@pytest.mark.django_db
def test_bookfile_create(create_bookfile):
    assert BookFile.objects.count() == 1
    found_book_list = BookFile.objects.first()
    assert found_book_list.file_name == create_bookfile.file_name
    assert found_book_list.date_uploaded.strftime(
        "%m/%d/%Y"
    ) == create_bookfile.date_uploaded.strftime("%m/%d/%Y")
