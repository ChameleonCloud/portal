from django.urls import path

from . import views

app_name = "allocations"

urlpatterns = [
    path("api/view/<str:charge_code>/", views.view_project, name="view_project"),
    path("approval/", views.approval, name="approval"),
    path("contact/", views.contact, name="contact"),
]
