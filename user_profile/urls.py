from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'user_profile.views',

    url(r'^$', 'profile', name='profile'),
    url(r'^edit/$', 'profile_edit', name='profile_edit'),
)
