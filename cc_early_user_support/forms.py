from django import forms
from . import models

class EarlyUserRequestForm(forms.ModelForm):

    class Meta:
        model = models.EarlyUserRequest
        fields = ['justification']

class EarlyUserRequestAdminForm(forms.ModelForm):

    class Meta:
        model = models.EarlyUserRequest
