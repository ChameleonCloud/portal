from django.views import generic
from .models import Artifact, Author

class IndexView(generic.ListView):
    template_name = 'sharing/index.html'
    context_object_name = 'artifacts'
    def get_queryset(self):
        return Artifact.objects.order_by('-created_at')

class DetailView(generic.DetailView):
    model = Artifact
    template_name = 'sharing/detail.html'
    def get_queryset(self):
        return Artifact.objects.filter()
