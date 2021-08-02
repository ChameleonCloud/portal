from django.urls import re_path
from . import views

app_name = "webinar_registration"

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    re_path(r"^webinar/(?P<id>\d+)/$", views.webinar, name="webinar"),
    re_path(r"^webinar/(?P<id>\d+)/register/$", views.register, name="register"),
    re_path(r"^webinar/(?P<id>\d+)/unregister/$", views.unregister, name="unregister"),
]
