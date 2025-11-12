from django.urls import path, re_path

from . import pub_views, views

app_name = "projects"

urlpatterns = [
    path("", views.user_projects, name="user_projects"),
    path("new/", views.create_project, name="create_project"),
    path("<int:project_id>/", views.view_project, name="view_project"),
    path("join/<str:invite_code>/", views.accept_invite, name="accept_invite"),
    path("join/request/<str:secret>/", views.request_to_join, name="reqeust_to_join"),
    path(
        "<int:project_id>/allocation/",
        views.create_allocation,
        name="create_allocation",
    ),
    path(
        "<int:project_id>/allocation/<int:allocation_id>",
        views.create_allocation,
        name="renew_allocation",
    ),
    path("api/extras/", views.get_extras, name="get_extras"),
    re_path(
        r"^add/publications(?:/(?P<project_id>\d+))?/$",
        pub_views.add_publications,
        name="add_publications",
    ),
    path("publications/", pub_views.user_publications, name="publications"),
    path("charge/<int:allocation_id>/", views.view_charge, name="view_charge"),
    path(
        "chameleon-used-research/",
        pub_views.view_chameleon_used_in_research_publications,
        name="chameleon_used_research",
    ),
    path(
        "<int:project_id>/project-member-export/",
        views.project_member_export,
        name="project_member_export",
    ),
]
