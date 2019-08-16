from django import forms
from datetime import datetime
from .models import Artifact, Author, Label
#from .models import Author, Label

class LabelForm(forms.Form):
    search = forms.CharField(required=False)
    label_options = [(str(label.id),label.label) for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)
    is_or = forms.BooleanField(required=False)

class UploadForm(forms.Form):
    label_options = [(str(label.id),label.label) for label in Label.objects.all()]

    artifact_options = [(str(artifact.id),artifact.title) for artifact in Artifact.objects.all()]

    #short_description = forms.CharField(max_length=70)
    #image = forms.ImageField(required=False,label="Icon image")
    #git_repo = forms.CharField(max_length=200, required=False)
    #labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)

    #associated_artifacts = forms.MultipleChoiceField(required=False, choices=artifact_options)
