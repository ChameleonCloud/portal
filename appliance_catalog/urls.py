from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "appliance_catalog"

urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            url="https://trovi.chameleoncloud.org/dashboard/artifacts?tags=appliance",
            permanent=True,
        ),
        name="app_list",
    ),
    path(
        "create/",
        RedirectView.as_view(
            url="https://chameleoncloud.readthedocs.io/en/latest/technical/complex/catalog.html",
            permanent=True,
        ),
        name="app_create",
    ),
    path("<int:pk>/", views.app_detail, name="app_detail"),
]
