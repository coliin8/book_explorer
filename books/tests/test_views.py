import pytest

from django.urls import reverse

import uuid

import pytest

from books.models import BookFile


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


# @pytest.mark.django_db
# def test_book_file_detail(auto_login_user, django_user_model, create_bookfile):
#     client, user = auto_login_user()
#     assert BookFile.objects.count() == 1
#     found_book_list = BookFile.objects.first()
#     print(found_book_list.pk)
#     url = reverse("books:detail", kwargs={"pk": found_book_list.pk})
#     response = client.get(url)
#     assert response.status_code == 200
#     assert "someone" in response.content.decode("utf-8")
