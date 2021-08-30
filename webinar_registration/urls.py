from django.urls import path
from . import views

app_name = "webinar_registration"

urlpatterns = [
    path("/", views.index, name="index"),
    path("webinar/<int:id>/", views.webinar, name="webinar"),
    path("webinar/<int:id>/register/", views.register, name="register"),
    path("webinar/<int:id>/unregister/", views.unregister, name="unregister"),
]
