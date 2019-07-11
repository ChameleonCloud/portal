from django import forms
from .models import Artifact, Author, Label

class LabelForm(forms.Form):
    label_options = [(label.id,label.label) for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)
        
