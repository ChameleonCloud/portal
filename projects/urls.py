from django.urls import path

from . import pub_views, views

app_name = "projects"

urlpatterns = [
    path("", views.user_projects, name="user_projects"),
    path("new/", views.create_project, name="create_project"),
    path("<int:project_id>/", views.view_project, name="view_project"),
    path("join/<str:invite_code>/", views.accept_invite, name="accept_invite"),
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
    path(
        "add/publications/<int:project_id>/",
        pub_views.add_publications,
        name="add_publications",
    ),
    path("publications/", pub_views.user_publications, name="publications"),
    path("charge/<int:allocation_id>/", views.view_charge, name="view_charge"),
]
