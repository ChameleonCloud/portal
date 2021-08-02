from django.urls import re_path
from . import views

app_name = "appliance_catalog"

urlpatterns = [
    re_path(r"^$", views.app_list, name="app_list"),
    re_path(r"^(?P<pk>\d+)/$", views.app_detail, name="app_detail"),
    re_path(r"^(?P<pk>\d+)/docs/$", views.app_documentation, name="app_documentation"),
    re_path(r"^(?P<pk>\d+)/edit/$", views.app_edit, name="app_edit"),
    re_path(r"^(?P<pk>\d+)/edit/image/$", views.app_edit_image, name="app_edit_image"),
    re_path(
        r"^(?P<pk>\d+)/delete/$", views.ApplianceDeleteView.as_view(), name="app_delete"
    ),
    re_path(r"^create/$", views.app_create, name="app_create"),
    re_path(r"^create/image/$", views.app_create_image, name="app_create_image"),
    re_path(
        r"^template/(?P<resource>.+?)\.html/$", views.app_template, name="app_template"
    ),
    re_path(r"^api/appliances/$", views.get_appliances, name="get_appliances"),
    re_path(
        r"^api/appliances/(?P<pk>\d+)/$", views.get_appliance, name="get_appliance"
    ),
    re_path(
        r"^api/appliances/appliance_id/(?P<appliance_id>[0-9a-f-]+)/$",
        views.get_appliance_by_id,
        name="get_appliance_by_id"
    ),
    re_path(
        r"^api/appliances/(?P<pk>\d+)/template$",
        views.get_appliance_template,
        name="get_appliance_template"
    ),
    re_path(r"^api/keywords/$", views.get_keywords, name="get_keywords"),
    re_path(
        r"^api/keywords/(?P<appliance_id>\d+)/$",
        views.get_keywords,
        name="get_keywords"
    ),
]
