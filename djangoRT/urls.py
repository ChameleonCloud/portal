from django.urls import re_path
from . import views

app_name = "django_rt"

urlpatterns = [
    re_path(r"^$", views.mytickets, name="mytickets"),
    re_path(r"^ticket/(?P<ticket_id>\d+)/$", views.ticketdetail, name="ticketdetail"),
    re_path(r"^ticket/new/$", views.ticketcreate, name="ticketcreate"),
    re_path(r"^ticket/reply/(?P<ticket_id>\d+)/$", views.ticketreply, name="ticketreply"),
    re_path(r"^ticket/new/guest/$", views.ticketcreateguest, name="ticketcreateguest"),
    re_path(r"^ticket/close/(?P<ticket_id>\d+)/$", views.ticketclose, name="ticketclose"),
    re_path(
        r"^ticket/attachment/(?P<ticket_id>\d+)/(?P<attachment_id>\d+)/$",
        views.ticketattachment,
        name="ticketattachment",
    ),
]
