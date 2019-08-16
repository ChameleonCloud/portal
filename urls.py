from django.urls import path
import sharing.views

urlpatterns = [
    path('', sharing.views.index, name='index'),
    path('upload', sharing.views.upload, name='upload'),
    path('<int:pk>', sharing.views.DetailView.as_view(), name='detail')
] 

