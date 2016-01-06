from django.forms import ModelForm
from .models import Appliance

class ApplianceForm(ModelForm):
	class Meta:
		model = Appliance
