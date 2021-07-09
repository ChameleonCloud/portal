from django.urls import re_path
from . import views

app_name = "blog_comments"

urlpatterns = [
    re_path(r'^post/(?P<pk>\d+)/comment/$', views.add_comment_to_post, name='add_comment_to_post'),
]
