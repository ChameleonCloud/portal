from django import forms
from . import models

class EarlyUserParticipantForm(forms.ModelForm):

    class Meta:
        model = models.EarlyUserParticipant
        fields = ['justification']


class EarlyUserProgramAdminForm(forms.ModelForm):

    class Meta:
        model = models.EarlyUserProgram
        fields = ['name', 'description', 'state']


class EarlyUserParticipantAdminForm(forms.ModelForm):

    class Meta:
        model = models.EarlyUserParticipant
        fields = ['user', 'program', 'justification', 'participant_status']
