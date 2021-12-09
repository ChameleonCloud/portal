from django.urls import path

from . import views

app_name = "balance_service"

urlpatterns = [
    path("", views.batch_get_project_allocations, name="batch_get_project_allocations"),
    path(
        "<int:project_id>/", views.get_project_allocation, name="get_project_allocation"
    ),
    path("v2/check-create/", views.check_create, name="check_create"),
    path("v2/check-update/", views.check_update, name="check_update"),
    path("v2/on-end/", views.on_end, name="on_end"),
]
