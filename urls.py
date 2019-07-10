from django.urls import path
from . import views

urlpatterns = [
    path('',views.IndexView.as_view(), name='index'),
    path('<int:pk>',views.DetailView.as_view(), name='detail'),
] 

#    Currently failing attempt to do filtering:
#    path('',views.FilterView.as_view(),name='index'),
