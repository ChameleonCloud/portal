from django.urls import re_path

from . import pub_views, views

app_name = "projects"

urlpatterns = [
    re_path(r"^$", views.user_projects, name="user_projects"),
    re_path(r"^new/$", views.create_project, name="create_project"),
    re_path(r"^(\d+)/$", views.view_project, name="view_project"),
    re_path(r"^join/([\w_-]+)/$", views.accept_invite, name="accept_invite"),
    re_path(r"^(\d+)/allocation/$", views.create_allocation, name="create_allocation"),
    re_path(
        r"^(\d+)/allocation/(\d+)$", views.create_allocation, name="renew_allocation"
    ),
    re_path(r"^api/extras/$", views.get_extras, name="get_extras"),
    re_path(
        r"^add/publications/(\d+)/$",
        pub_views.add_publications,
        name="add_publications",
    ),
    re_path(r"^publications/$", pub_views.user_publications, name="publications"),
]
