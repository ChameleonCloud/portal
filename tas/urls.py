from django.urls import re_path
from . import views

app_name = "tas"

urlpatterns = [
    re_path(r"^profile/$", views.profile, name="profile"),
    re_path(r"^profile/edit/$", views.profile_edit, name="profile_edit"),
]
