from django.forms import ModelForm
from .models import Downtime

class DowntimeForm(ModelForm):
	class Meta:
		model = Downtime
		fields = ['queue', 'nodes_down', 'start', 'end', 'description']
