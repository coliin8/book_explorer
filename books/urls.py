from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm

from . import views

app_name = "books"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    # path('<int:pk>/', views.DetailView.as_view(), name='detail'),
    path("<int:pk>/", views.detail, name="detail"),
    # path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
    # path('<int:question_id>/vote/', views.vote, name='vote'),
    path("register/", views.register_request, name="register"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("upload", views.upload, name="upload"),
]
