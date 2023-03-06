import logging

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

from .validators import BookListCsvValidator
from .tasks import (
    process_notification_task,
    retrieve_json_from_s3_task,
    upload_csv_to_s3_task,
)
from .helpers import (
    convert_csv_to_dict_helper,
    check_csv_upload_state_helper,
)
from .models import BookFile
from .forms import NewUserForm

logger = logging.getLogger(__name__)


S3_BUCKET_NAME: str = "jc1976bucket"
AWS_REGION_NAME: str = "eu-west-1"


def set_message(message_type, request, message):
    getattr(messages, message_type)(request, message)
    getattr(logger, message_type)(message)


def set_message_and_redirect(
    message_type, request, message, url
) -> HttpResponseRedirect:
    set_message(message_type, request, message)
    return redirect(url)


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
    logger.info(f"Retreiving BookList {pk}")
    book_list = get_object_or_404(BookFile, pk=pk)

    # Guard Checks, is csv uploaded yet or if there has been an unexpected error
    async_result = retrieve_json_from_s3_task.delay(
        S3_BUCKET_NAME, book_list.s3_file_name
    )
    action_result = check_csv_upload_state_helper(async_result, 5)
    if action_result.is_success == False:
        return set_message_and_redirect(
            "error",
            request,
            f"Unexpected failure retrieve file from AWS S3 - {action_result.message}",
            "books:index",
        )
    elif action_result.message:
        return set_message_and_redirect(
            "info",
            request,
            f"Try again later. Failed to retrieve csv data from AWS S3 - {action_result.message}",
            "books:index",
        )
    logging.info(f"Successfully retrived S3 file {book_list.s3_file_name}")
    return render(
        request,
        "books/detail.html",
        {"book_list": book_list, "csv_row_list": action_result.result_object["rows"]},
    )


def register_request(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """Render new User Form for Book Explorer if http method is GET, or if POST then generate new User
    for Book Explorer App.

    Args:
        request (HttpRequest): Register form data

    Returns:
        HttpResponse | HttpResponseRedirect: redirect to
    """
    logger.info(f"Regitering User {user}")
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            logger.info(f"Successfully Registered User {user}")
            return redirect("books:index")
        logger.error(f"Unsuccessful registration. Invalid information. {user}")
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
    """Simple user logout method that will return you to home page

    Args:
        request (HttpRequest): _description_

    Returns:
        HttpResponseRedirect | HttpResponsePermanentRedirect: _description_
    """
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("books:index")


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
    if request.method != "POST" or not request.FILES["upload"]:
        return set_message_and_redirect(
            "info", request, "No file was uploaded.", "books:index"
        )
    # Validate CSV file
    file_to_upload = request.FILES["upload"]
    manager = BookListCsvValidator()
    action_result = manager.validate(file_to_upload)

    if not action_result.is_success:
        return set_message_and_redirect(
            "error",
            request,
            action_result.message,
            "books:index",
        )
    db_book_file = action_result.result_object
    # Upload file to s3
    async_result = upload_csv_to_s3_task.delay(
        AWS_REGION_NAME,
        S3_BUCKET_NAME,
        db_book_file.s3_file_name,
        convert_csv_to_dict_helper(file_to_upload),
    )
    action_result = check_csv_upload_state_helper(async_result, 3)
    # Save database row or raise error to user
    if not action_result.is_success:
        return set_message_and_redirect(
            "error",
            request,
            f"Failed Unexpectedly to Upload {db_book_file.file_name} - {action_result.message}.",
            "books:index",
        )
    # Save Book list details to database
    db_book_file.save()
    saved_db_book_file = BookFile.objects.filter(s3_url=db_book_file.s3_url).first()
    # Notification to 3rd Party
    process_notification_task.delay(db_book_file.s3_url)
    set_message("info", request, f"You have successfully create {db_book_file}.")
    return redirect("books:detail", saved_db_book_file.id)
