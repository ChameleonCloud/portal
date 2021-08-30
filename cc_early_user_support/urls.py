from django.urls import path, re_path
from . import views

app_name = "cc_early_user_support"

urlpatterns = [
    path("/", views.index, name="index"),
    path("program/<int:id>/", views.view_program, name="program"),
    path(
        "program/<int:id>/participate/",
        views.request_to_participate,
        name="participate",
    ),
    re_path(
        r"^program/(?P<id>\d+)/export_participants\.txt$",
        views.participants_export_list,
    ),
    re_path(
        r"^program/(?P<id>\d+)/export_participants/(?P<list_type>\w+)\.txt$",
        views.participants_export_list,
    ),
]
