from django.conf.urls import url
import views

urlpatterns = [
    url(r'^add/$', views.add_publications, name='add_publications'),
    url(r'^$', views.user_publications, name='publications'),
    ]

# url(r'^new/$', views.create_project, name='create_project'),