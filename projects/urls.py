from django.conf.urls import url

from . import pub_views, views

urlpatterns = [
    url(r"^$", views.user_projects, name="user_projects"),
    url(r"^new/$", views.create_project, name="create_project"),
    url(r"^(\d+)/$", views.view_project, name="view_project"),
    url(r"^join/(\d+)", views.accept_invite, name="accept_invite"),
    url(r"^(\d+)/allocation/$", views.create_allocation, name="create_allocation"),
    url(r"^(\d+)/allocation/(\d+)$", views.create_allocation, name="renew_allocation"),
    url(r"^api/extras/$", views.get_extras, name="get_extras"),
    url(
        r"^add/publications/(\d+)/$",
        pub_views.add_publications,
        name="add_publications",
    ),
    url(r"^publications/$", pub_views.user_publications, name="publications"),
]
