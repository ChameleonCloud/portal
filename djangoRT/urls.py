from django.urls import path
from . import views

app_name = "django_rt"

urlpatterns = [
    path("", views.mytickets, name="mytickets"),
    path("ticket/<int:ticket_id>/", views.ticketdetail, name="ticketdetail"),
    path("ticket/new/", views.ticketcreate, name="ticketcreate"),
    path(
        "ticket/reply/<int:ticket_id>/", views.ticketreply, name="ticketreply"
    ),
    path("ticket/new/guest/", views.ticketcreateguest, name="ticketcreateguest"),
    path(
        "ticket/close/<int:ticket_id>/", views.ticketclose, name="ticketclose"
    ),
    path(
        "ticket/attachment/<int:ticket_id>/<int:attachment_id>/",
        views.ticketattachment,
        name="ticketattachment",
    ),
]
