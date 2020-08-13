from django import forms

from .models import Artifact, ArtifactVersion, Author, Label


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
        fields = ('title', 'short_description', 'description',)


class ArtifactVersionForm(forms.ModelForm):
    readonly_fields = ('deposition_id', 'deposition_repo',)

    def __init__(self, *args, **kwargs):
        super(ArtifactVersionForm, self).__init__(*args, **kwargs)
        for readonly_field in self.readonly_fields:
            self.fields[readonly_field].widget.attrs['readonly'] = True

    class Meta:
        model = ArtifactVersion
        fields = ('deposition_id', 'deposition_repo',)


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ('name', 'affiliation',)

    def save(self, commit=True):
        # Perform a lookup to see if this field combo already exists.
        # If it does, then just return it from the DB. Else, create a new
        # entry. This allows users to add new authors, but it avoids creating
        # duplicates.
        try:
            self.instance = self.Meta.model.objects.get(
                name=self.instance.name,
                affiliation=self.instance.affiliation)
        except self.Meta.model.DoesNotExist:
            pass

        return super(AuthorForm, self).save(commit=commit)


AuthorFormset = forms.modelformset_factory(
    AuthorForm.Meta.model, form=AuthorForm, can_delete=True,
    extra=2, min_num=1, max_num=3)
