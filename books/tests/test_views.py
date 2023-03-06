import pytest
import uuid

import pytest
from django.urls import reverse
from django.test.client import MULTIPART_CONTENT, encode_multipart, BOUNDARY
from bs4 import BeautifulSoup

from books.models import BookFile

from . import StubAsyncResult
from .constants import VALID_CSV_JSON


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def create_user(db, django_user_model, test_password):
    def make_user(**kwargs):
        kwargs["password"] = test_password
        if "username" not in kwargs:
            kwargs["username"] = str(uuid.uuid4())
        return django_user_model.objects.create_user(**kwargs)

    return make_user


@pytest.fixture
def auto_login_user(db, client, create_user, test_password):
    def make_auto_login(user=None):
        if user is None:
            user = create_user()
        client.login(username=user.username, password=test_password)
        return client, user

    return make_auto_login


@pytest.mark.django_db
def test_book_file_homepage(auto_login_user):
    client, user = auto_login_user()
    response = client.get(reverse("books:index"))
    assert response.status_code == 200
    assert "Current Book list Files" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_book_file_detail(mocker, auto_login_user, django_user_model, create_bookfile):
    # Setup
    stub_async_result = StubAsyncResult("fd9h9gudgys8", "SUCCESS", VALID_CSV_JSON)
    mock_retrieve_task = mocker.patch(
        "books.views.retrieve_json_from_s3_task.delay", return_value=stub_async_result
    )
    client, _ = auto_login_user()
    assert BookFile.objects.count() == 1
    found_book_list = BookFile.objects.first()
    # Actions
    url = reverse("books:detail", kwargs={"pk": found_book_list.pk})
    response = client.get(url)
    # Assertions
    mock_retrieve_task.assert_called_once_with(
        "jc1976bucket", found_book_list.s3_file_name
    )
    content = response.content.decode("utf-8")
    assert response.status_code == 200
    soup = BeautifulSoup(content)
    trs = soup.find_all("tr")
    assert len(trs) == 10
    for value in ["aaa", "bbb", "ccc", "ddd"]:
        assert value in content
    assert mock_retrieve_task


@pytest.mark.django_db
def test_book_list_upload_success(
    mocker, auto_login_user, django_user_model, csv_file_like_object
):
    # Setup
    stub_async_result = StubAsyncResult("fd9h9gudgys8", "SUCCESS", VALID_CSV_JSON)
    mock_upload_task = mocker.patch(
        "books.views.upload_csv_to_s3_task.delay", return_value=stub_async_result
    )
    mock_notify_task = mocker.patch("books.views.process_notification_task.delay")
    d_client, _ = auto_login_user()
    response = d_client.post(reverse("books:upload"), {"upload": csv_file_like_object})
    # Assertions
    # we do a redirect hence not 201
    messages = list(response.wsgi_request._messages)
    assert response.status_code == 302
    assert "You have successfully create book-success.csv - " in messages[0].message
    mock_upload_task.assert_called_once()
    mock_notify_task.assert_called_once()


@pytest.mark.django_db
def test_book_list_upload_failed_validation(
    mocker, auto_login_user, django_user_model, csv_file_like_object_validation_errors
):
    # Setup
    stub_async_result = StubAsyncResult("fd9h9gudgys8", "SUCCESS", VALID_CSV_JSON)
    mock_upload_task = mocker.patch(
        "books.views.upload_csv_to_s3_task.delay", return_value=stub_async_result
    )
    mock_notify_task = mocker.patch("books.views.process_notification_task.delay")
    d_client, _ = auto_login_user()
    response = d_client.post(
        reverse("books:upload"), {"upload": csv_file_like_object_validation_errors}
    )
    # Assertions
    # we do a redirect hence not 201
    messages = list(response.wsgi_request._messages)
    assert response.status_code == 302
    assert (
        "Failed to upload book-failure.csv due to validation - CSV"
        in messages[0].message
    )
    mock_upload_task.assert_not_called()
    mock_notify_task.assert_not_called()
