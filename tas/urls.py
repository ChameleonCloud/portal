from django.conf.urls import url

from . import views

app_name = "tas"

urlpatterns = [
    url(r"^profile/", views.profile, name="profile"),
    url(r"^profile/edit/", views.profile_edit, name="profile_edit"),
]
