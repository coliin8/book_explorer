from django.http import (
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render, redirect
from django.views import generic
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from books.tasks import task_process_notification

from .storage import S3UploadFileManager
from .models import BookFile
from .forms import NewUserForm


class IndexView(LoginRequiredMixin, generic.ListView):
    paginate_by = 10
    model = BookFile
    template_name = "books/index.html"


@login_required
def detail(request, pk):
    book_list = get_object_or_404(BookFile, pk=pk)
    manager = S3UploadFileManager()
    s3_file = manager.retrieve(book_list)
    csv_row_list = manager.csv_file_object_to_dict(s3_file)
    return render(
        request,
        "books/detail.html",
        {"book_list": book_list, "csv_row_list": csv_row_list["rows"]},
    )


def register_request(request) -> HttpResponse:
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
def logout_request(request) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("books:index")


@login_required
def upload(request) -> HttpResponseRedirect | HttpResponsePermanentRedirect:
    if request.method == "POST" and request.FILES["upload"]:
        upload = request.FILES["upload"]
        manager = S3UploadFileManager()
        db_book_file = manager.upload(upload)
        db_book_file.save()
        saved_db_book_file = BookFile.objects.filter(s3_url=db_book_file.s3_url).first()
        messages.info(request, f"You have successfully create {db_book_file}.")
        # Don't waste url time with notification can be handled by celery
        task_process_notification.delay(db_book_file.s3_url)
        return redirect("books:detail", saved_db_book_file.id)

    messages.info(request, f"No file was uploaded.")
    return redirect("books:index")
