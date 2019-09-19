from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^forgot-username/$', views.recover_username, name='recover_username'),
    url(r'^register/$', views.register, name='register'),
    url(r'^password-reset/$', views.password_reset, name='password_reset'),
    url(r'^email-confirmation/$', views.email_confirmation, name='email_confirmation'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^profile/edit/$', views.profile_edit, name='profile_edit'),
    url(r'^departments\.json$', views.get_departments_json),
]
