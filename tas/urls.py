from django.conf.urls import patterns, url

urlpatterns = patterns(
    'tas.views',
    url( r'^register/$', 'register', name='register' ),
    url( r'^password-reset/$', 'password_reset', name='password_reset' ),
    url( r'^email-confirmation/$', 'email_confirmation', name='email_confirmation' ),
    url( r'^profile/$', 'profile', name='profile' ),
    url( r'^profile/edit/$', 'profile_edit', name='profile_edit' ),
)
