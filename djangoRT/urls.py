from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.mytickets, name="mytickets"),
    url(r"^ticket/(?P<ticket_id>\d+)/$", views.ticketdetail, name="ticketdetail"),
    url(r"^ticket/new/$", views.ticketcreate, name="ticketcreate"),
    url(r"^ticket/reply/(?P<ticket_id>\d+)/$", views.ticketreply, name="ticketreply"),
    url(r"^ticket/new/guest/$", views.ticketcreateguest, name="ticketcreateguest"),
    url(r"^ticket/close/(?P<ticket_id>\d+)/$", views.ticketclose, name="ticketclose"),
    url(
        r"^ticket/attachment/(?P<ticket_id>\d+)/(?P<attachment_id>\d+)/$",
        views.ticketattachment,
        name="ticketattachment",
    ),
]
