from django.urls import path, re_path
from . import views

app_name = "g5k_discovery"

urlpatterns = [
    path("/", views.index, name="discovery"),
    re_path(r"^node/(?P<resource>.+?)\.json/$", views.node_data, name="node_json"),
    re_path(r"^node/(?P<resource>.+?)/$", views.node_view, name="node_detail"),
    re_path(r"^(?P<resource>.+?)\.json$", views.g5k_json, name="discovery_json"),
    re_path(
        r"^template/(?P<resource>.+?)\.html/$", views.g5k_html, name="discovery_html"
    ),
]
