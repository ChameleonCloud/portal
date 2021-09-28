from django.db.models import Q
from django.core.exceptions import ValidationError
from django import forms
from django.forms import widgets

from projects.models import Project
from util.project_allocation_mapper import ProjectAllocationMapper

from .models import Artifact, ArtifactVersion, Author, Label, DayPassRequest

import logging

LOG = logging.getLogger(__name__)


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        fields = (
            "title",
            "short_description",
            "description",
            "labels",
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        # Only allow staff members to use the special "Chameleon-supported"
        # label on the artifact.
        if self.request.user.is_staff:
            available_labels = Label.objects.all()
        else:
            available_labels = Label.objects.filter(~Q(label=Label.CHAMELEON_SUPPORTED))

        self.fields["labels"] = forms.ModelMultipleChoiceField(
            available_labels, required=False)

    def clean_labels(self):
        labels = self.cleaned_data["labels"]
        # Ensure only staff members can save w/ the "chameleon" label.
        if (
            any(l.label == Label.CHAMELEON_SUPPORTED for l in labels)
            and not self.request.user.is_staff
        ):
            raise ValidationError("Invalid label")
        return labels


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

    is_public = forms.BooleanField(
        label="Enable all users to find and share",
        required=False,
        widget=widgets.CheckboxInput(attrs={"v-model": "is_public"}),
    )
    is_reproducible = forms.BooleanField(
        label="Enable reproducibility requests",
        required=False,
        widget=widgets.CheckboxInput(attrs={"v-model": "is_reproducible"}),
    )
    reproduce_hours = forms.IntegerField(
        label="Hours a user has to reproduce", required=False
    )
    projects = ProjectChoiceField(
        label="Share with projects", required=False, queryset=Project.objects.all()
    )

    # Custom init is required to dynamically fill the projects choice field

    def __init__(self, request, *args, **kwargs):
        super(ShareArtifactForm, self).__init__(*args, **kwargs)
        mapper = ProjectAllocationMapper(request)
        user_projects = [
            (
                project["chargeCode"],
                project["nickname"] if "nickname" in project else project["chargeCode"],
            )
            for project in mapper.get_user_projects(
                request.user.username, to_pytas_model=False
            )
        ]
        self.fields["project"] = forms.ChoiceField(
            label="Belongs to project",
            required=False,
            choices=[(None, "----")] + user_projects,
        )

    def clean(self):
        data = self.cleaned_data
        if data.get("is_reproducible", None) and not data.get("reproduce_hours", None):
            raise forms.ValidationError(
                "You must include hours when enabling reproducibility requests"
            )
        if data.get("is_reproducible", None) and not data.get("project", None):
            raise forms.ValidationError(
                "You must associate this artifact with a project to enable reproducibility requests"
            )
        return data


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


ZenodoPublishFormset = forms.formset_factory(
    ZenodoPublishForm, formset=BaseZenodoPublishFormset, extra=0
)


class RequestDayPassForm(forms.Form):
    name = forms.CharField()
    email = forms.CharField(disabled=True, required=False)
    institution = forms.CharField()
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": "Reason for request"}),
    )


class ReviewDayPassForm(forms.Form):
    status = forms.ChoiceField(required=True, choices=DayPassRequest.STATUS)

    def clean(self):
        data = self.cleaned_data
        if data.get("status", None) == DayPassRequest.STATUS_PENDING:
            raise forms.ValidationError("You must set a status")
