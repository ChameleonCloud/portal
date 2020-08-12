from django import forms

from .models import Artifact, Label


class LabelForm(forms.Form):
    """
    Form to allow search on the index page
    """

    class LabelChoiceField(forms.ModelChoiceField):
        """
        Custom model choice field that can display a choice
        of existing Label models.
        """
        def label_from_instance(self, obj):
            return str(obj.id)

    search = forms.CharField(required=False)
    labels = LabelChoiceField(label='Labels', required=False,
                              queryset=Label.objects.all())
    is_or = forms.BooleanField(required=False)


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        fields = ['title', 'short_description', 'description',
                  'labels', 'authors']
