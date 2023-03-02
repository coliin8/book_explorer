from typing import IO, Tuple
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render, redirect
from django.views import generic
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from books.tasks import task_process_notification

from .storage import CsvFileExistsError, CsvFileValidationError, S3UploadFileManager
from .models import BookFile
from .forms import NewUserForm


class IndexView(LoginRequiredMixin, generic.ListView):
    paginate_by = 10
    model = BookFile
    template_name = "books/index.html"


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Returns details of BookFile from Database row and S3 File. Allow contents of cvs to to
    displayed on page.

    Args:
        request (HttpRequest): Http Request
        pk (int): id of BookList

    Returns:
        HttpResponse: Page to display
    """
    book_list = get_object_or_404(BookFile, pk=pk)
    manager = S3UploadFileManager()
    s3_file = manager.retrieve(book_list)
    csv_row_list = manager.csv_file_object_to_dict(s3_file)
    return render(
        request,
        "books/detail.html",
        {"book_list": book_list, "csv_row_list": csv_row_list["rows"]},
    )


def register_request(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("books:index")
        messages.error(request, "Unsuccessful registration. Invalid information.")
    form = NewUserForm()
    return render(
        request=request,
        template_name="books/register.html",
        context={"register_form": form},
    )


@login_required
def logout_request(
    request: HttpRequest,
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("books:index")


def upload_file_to_cloud(upload: IO) -> Tuple[bool, str | None, BookFile | None]:
    """Try to upload Csv file to Cloud

    Args:
        upload (IO): File Like Object to upload to cloud
    Returns:
        Tuple(bool, str): Details of Success or failure
    """
    manager = S3UploadFileManager()
    is_success = True
    message, db_book_file = None, None
    try:
        db_book_file = manager.upload(upload)
    except (CsvFileExistsError, CsvFileValidationError) as e:
        message = f"Failed to upload {upload.name} due to validation - {e}."
        is_success = False
    except Exception as e:
        message = f"Failed Unexpectedly to Upload {upload.name} - {e}."
        is_success = False
    return (
        is_success,
        message,
        db_book_file,
    )


@login_required
def upload(
    request: HttpRequest,
) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    """View will upload a CSV file to S3 Bucket and store a BookList in the database.

    This might fail due to Validation or a file already existing.

    If successful will trigger a Celery Task to send S3 Url to 3rd Party Interface as Async.

    Args:
        request (HttpRequest): Http Request

    Returns:
        HttpResponseRedirect | HttpResponsePermanentRedirect: Will Redirect to required page.
    """
    if request.method == "POST" and request.FILES["upload"]:
        uploade_success, upload_message, db_book_file = upload_file_to_cloud(
            request.FILES["upload"]
        )
        if not uploade_success:
            messages.error(request, upload_message)
            return redirect("books:index")
        db_book_file.save()
        saved_db_book_file = BookFile.objects.filter(s3_url=db_book_file.s3_url).first()
        messages.info(request, f"You have successfully create {db_book_file}.")
        # Don't waste url time with notification can be handled by celery
        task_process_notification.delay(db_book_file.s3_url)
        return redirect("books:detail", saved_db_book_file.id)

    messages.info(request, "No file was uploaded.")
    return redirect("books:index")
