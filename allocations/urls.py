from django.urls import path, re_path

from . import views

app_name = "allocations"

urlpatterns = [
    path("/", views.index, name="index"),
    path("view/", views.view, name="view"),
    path("json/", views.return_json, name="return_json"),
    path("approval/", views.approval, name="approval"),
    path("contact/", views.contact, name="contact"),
    path("denied/", views.denied, name="denied"),
    path("user/", views.user_select, name="user_select"),
    path("user/<str:username>/", views.user_projects, name="user_projects"),
    re_path(
        r"^template/(?P<resource>.+?)\.html/$",
        views.allocations_template,
        name="allocations_template",
    ),
]
