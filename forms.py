from django import forms

from .models import Label  # , Artifact


class LabelForm(forms.Form):
    """
    Form to allow search on the index page
    """
    # Text input search
    search = forms.CharField(required=False)

    # Labels to allow user to choose from
    label_options = [(str(label.id), label.label)
                     for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels', required=False,
                                       choices=label_options)

    # Boolean and vs or search style
    is_or = forms.BooleanField(required=False)


class UploadForm(forms.Form):
    """
    Form to allow users to add additional information after a Zenodo upload
    Currently not in use to minimize user clicks
    """
    # label_options = [(str(label.id),label.label)
    #                  for label in Label.objects.all()]

    # artifact_options = [(str(artifact.id),artifact.title)
    #                     for artifact in Artifact.objects.all()]
    #
    # short_description = forms.CharField(max_length=70)
    # image = forms.ImageField(required=False,label="Icon image")
    # git_repo = forms.CharField(max_length=200, required=False)
    # labels = forms.MultipleChoiceField(label='Labels',required=False,
    #                                   choices=label_options)
    # associated_artifacts = forms.MultipleChoiceField(required=False,
    #                                                 choices=artifact_options)
