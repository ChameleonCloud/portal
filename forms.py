from django import forms
from .models import Artifact, Author, Label

class LabelForm(forms.Form):
    search = forms.CharField(required=False)
    label_options = [(str(label.id),label.label) for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)
    is_or = forms.BooleanField(required=False)
