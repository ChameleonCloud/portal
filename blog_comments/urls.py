from django.conf.urls import url

from . import views

app_name = "blog_comments"

urlpatterns = [
    url(
        r"^post/(?P<pk>\d+)/comment/$",
        views.add_comment_to_post,
        name="add_comment_to_post",
    ),
]
