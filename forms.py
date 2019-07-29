from django import forms
from datetime import datetime
from .models import Artifact, Author, Label

class LabelForm(forms.Form):
    search = forms.CharField(required=False)
    label_options = [(str(label.id),label.label) for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)
    is_or = forms.BooleanField(required=False)

class UploadForm(forms.Form):
    label_options = [(str(label.id),label.label) for label in Label.objects.all()]
    artifact_options = [(str(artifact.id),artifact.title) for artifact in Artifact.objects.all()]

    # author_options = [(str(author.id), author.full_name) for author in Author.objects.all()]
    # title = forms.CharField(max_length=200)
    # authors = forms.MultipleChoiceField(required=False, choices=author_options)

    short_description = forms.CharField(max_length=70,required=False)

    # description = forms.CharField(max_length=5000)
    image = forms.ImageField(required=False,label="Icon image")
    git_repo = forms.CharField(max_length=200, required=False)
    # launchable = forms.BooleanField(required=False)
    # created_at = forms.DateTimeField(initial=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), required=False)
    # updated_at = forms.DateTimeField(initial=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), required=False)
#    updated_at = forms.DateTimeField()
    labels = forms.MultipleChoiceField(label='Labels',required=False, choices=label_options)
    associated_artifacts = forms.MultipleChoiceField(required=False, choices=artifact_options)

    '''
    def upload(self):
        data = self.cleaned_data
        item = Artifact(
            title=data.title,
            short_description = data.short_description,
            description = data.description,
            image = data.image,
            doi = data.doi,
            git_repo = data.git_repo,
            launchable = data.launchable,
            created_at = data.created_at,
            updated_at = data.updated_at,
        )
        item.save()
        item.associated_artifacts.set(data.associated_artifacts)
        item.labels.set(data.labels)
        item.authors.set(data.authors)
        item.save()
    '''

            
