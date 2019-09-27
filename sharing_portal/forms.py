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

    
    # Text input search
    search = forms.CharField(required=False)

    # Labels to allow user to choose from
    labels = LabelChoiceField(label='Labels', required=False,
                              queryset=Label.objects.all())

    # Boolean and vs or search style
    is_or = forms.BooleanField(required=False)


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        fields = ['title', 'short_description', 'description', 
                  'image', 'labels', 'authors', 'doi']
        widgets = {
            'doi': forms.TextInput(attrs={'readonly': True}),
        }
        