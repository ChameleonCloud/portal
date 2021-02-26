from django import forms

from projects.models import Project

from .models import Artifact, ArtifactVersion, Author, Label


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        fields = ('title', 'short_description', 'description', 'labels',)


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


class ShareArtifactForm(forms.Form):
    class ProjectChoiceField(forms.ModelMultipleChoiceField):
        def label_from_instance(self, project):
            return project.nickname or project.charge_code

    is_public = forms.BooleanField(label='Enable all users to find and share', required=False)
    projects = ProjectChoiceField(label='Share with projects', required=False,
        queryset=Project.objects.all())


class ZenodoPublishForm(forms.Form):
    artifact_version_id = forms.CharField(widget=forms.HiddenInput())
    request_doi = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        label = kwargs.pop('label', 'Request DOI')
        force_disable = kwargs.pop('force_disable', False)
        super(ZenodoPublishForm, self).__init__(*args, **kwargs)
        doi_field = self.fields['request_doi']
        doi_field.disabled = self._has_doi() or force_disable
        if self._has_doi():
            doi_field.label = 'Published as {}'.format(self.model.doi)
        else:
            doi_field.label = label

    def get_initial_for_field(self, field, field_name):
        if field_name == 'artifact_version_id':
            return self.model.pk
        elif field_name == 'request_doi':
            return self._has_doi()
        return None

    def clean(self):
        """Override clean to avoid setting form data when a DOI is assigned.

        This prevents duplicate requests to try to request a DOI for an
        artifact version.
        """
        if self._has_doi():
            self.cleaned_data = {}
        return super(ZenodoPublishForm, self).clean()

    def _has_doi(self):
        return self.model.doi is not None


class BaseZenodoPublishFormset(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        artifact_versions = kwargs.pop('artifact_versions')
        if not artifact_versions:
            raise ValueError('artifact_versions must provided')
        self.artifact_versions = artifact_versions
        self.latest_published_version = max([
            i for i, v in enumerate(artifact_versions) if v.doi
        ] or [-1])
        kwargs['initial'] = [{} for _ in artifact_versions]
        super(BaseZenodoPublishFormset, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        """Pass the linked artifact version model through to the nested form.
        """
        future_version_published = index < self.latest_published_version
        return {
            'model': self.artifact_versions[index],
            # Prevent publishing versions behind the latest published version
            'force_disable': future_version_published,
            'label': ('(cannot request DOI for past versions)'
                if future_version_published else None)
        }

    @property
    def cleaned_data(self):
        """Override cleaned_data to ignore forms with empty data.
        """
        return [x for x in super(BaseZenodoPublishFormset, self).cleaned_data if x]


ZenodoPublishFormset = forms.formset_factory(ZenodoPublishForm,
    formset=BaseZenodoPublishFormset, extra=0)
