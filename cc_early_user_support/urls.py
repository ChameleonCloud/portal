from django.urls import re_path
from . import views

app_name = "cc_early_user_support"

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^program/(?P<id>\d+)/$", views.view_program, name="program"),
    re_path(
        r"^program/(?P<id>\d+)/participate/$",
        views.request_to_participate,
        name="participate"
    ),
    re_path(
        r"^program/(?P<id>\d+)/export_participants\.txt$",
        views.participants_export_list
    ),
    re_path(
        r"^program/(?P<id>\d+)/export_participants/(?P<list_type>\w+)\.txt$",
        views.participants_export_list
    ),
]
