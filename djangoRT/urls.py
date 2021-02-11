from django.conf.urls import url

from . import views

app_name = "django_rt"

urlpatterns = [
    url(r"^", views.mytickets, name="mytickets"),
    url(r"^ticket/(?P<ticketId>\d+)/", views.ticketdetail, name="ticketdetail"),
    url(r"^ticket/new/", views.ticketcreate, name="ticketcreate"),
    url(r"^ticket/reply/(?P<ticketId>\d+)/", views.ticketreply, name="ticketreply"),
    url(r"^ticket/new/guest/", views.ticketcreateguest, name="ticketcreateguest"),
    url(r"^ticket/close/(?P<ticketId>\d+)/", views.ticketclose, name="ticketclose"),
    url(
        r"^ticket/attachment/(?P<ticketId>\d+)/(?P<attachmentId>\d+)/$",
        views.ticketattachment,
        name="ticketattachment",
    ),
]
