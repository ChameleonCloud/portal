from django.urls import re_path

from . import views

app_name = "allocations"

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^view/$", views.view, name="view"),
    re_path(r"^json/$", views.return_json, name="return_json"),
    re_path(r"^approval/$", views.approval, name="approval"),
    re_path(r"^contact/$", views.contact, name="contact"),
    re_path(r"^denied/$", views.denied, name="denied"),
    re_path(r"^user/$", views.user_select, name="user_select"),
    re_path(r"^user/(?P<username>.+?)/$", views.user_projects, name="user_projects"),
    re_path(
        r"^template/(?P<resource>.+?)\.html/$",
        views.allocations_template,
        name="allocations_template",
    ),
]
