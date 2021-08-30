from django.urls import path
from . import views

app_name = "tas"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
]
