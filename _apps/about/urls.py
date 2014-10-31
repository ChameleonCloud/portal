
from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static

from about import views

urlpatterns = patterns('',
    url(r'^$', views.about, name='about'),
    url(r'^schedule/$', views.schedule, name='schedule'),
    #url(r'^team/$', views.TeamMembersView.as_view(), name='team_members'),
    url(r'^team/$', views.teamMembers, name='team_members'),
    url(r'^team/(?P<pk>\S+)/$', views.TeamMemberView.as_view(), name='team_member'),
)
