from django.urls import path, re_path
from . import views

app_name = "appliance_catalog"

urlpatterns = [
    path("", views.app_list, name="app_list"),
    path("<int:pk>/", views.app_detail, name="app_detail"),
    path("<int:pk>/docs/", views.app_documentation, name="app_documentation"),
    path("<int:pk>/edit/", views.app_edit, name="app_edit"),
    path("<int:pk>/edit/image/", views.app_edit_image, name="app_edit_image"),
    path(
        "<int:pk>/delete/", views.ApplianceDeleteView.as_view(), name="app_delete"
    ),
    path("create/", views.app_create, name="app_create"),
    path("create/image/", views.app_create_image, name="app_create_image"),
    re_path(
        r"^template/(?P<resource>.+?)\.html/$", views.app_template, name="app_template"
    ),
    path("api/appliances/", views.get_appliances, name="get_appliances"),
    path(
        "api/appliances/<int:pk>/", views.get_appliance, name="get_appliance"
    ),
    path(
        "api/appliances/appliance_id/<uuid:appliance_id>/",
        views.get_appliance_by_id,
        name="get_appliance_by_id",
    ),
    path(
        "api/appliances/<int:pk>/template",
        views.get_appliance_template,
        name="get_appliance_template",
    ),
    path("api/keywords/", views.get_keywords, name="get_keywords"),
    path(
        "api/keywords/<int:appliance_id>/",
        views.get_keywords,
        name="get_keywords",
    ),
]
