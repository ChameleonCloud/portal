from django import forms
from django.forms import widgets, CheckboxSelectMultiple

from projects.models import Project
from util.project_allocation_mapper import ProjectAllocationMapper

from .models import DaypassRequest
from . import trovi

import logging

LOG = logging.getLogger(__name__)


class ArtifactForm(forms.Form):
    title = forms.CharField(label="Title")
    short_description = forms.CharField(label="Short Description")
    long_description = forms.CharField(
        label="Long Description", widget=forms.Textarea(), required=False
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request")
        artifact = kwargs.pop("artifact", None)
        super().__init__(*args, **kwargs)

        available_labels = [
            (t["tag"], t["tag"])
            for t in trovi.list_tags(request.session.get("trovi_token"))
        ]
        self.fields["tags"] = forms.MultipleChoiceField(
            widget=CheckboxSelectMultiple,
            choices=available_labels,
            required=False,
            initial=artifact["tags"] if artifact else [],
        )
        if artifact:
            self.fields["title"].initial = artifact["title"]
            self.fields["long_description"].initial = artifact["long_description"]
            self.fields["short_description"].initial = artifact["short_description"]


class AuthorForm(forms.Form):
    full_name = forms.CharField(label="Full Name")
    email = forms.CharField(label="Email")
    affiliation = forms.CharField(label="Affiliation", required=False)
    prefix = "author"

    def __init__(self, *args, **kwargs):
        author = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)

        if author:
            self.fields["full_name"].initial = author["full_name"]
            self.fields["email"].initial = author["email"]
            self.fields["affiliation"].initial = author["affiliation"]


AuthorFormset = forms.formset_factory(
    form=AuthorForm, can_delete=True, extra=2, min_num=1
)

AuthorCreateFormset = forms.formset_factory(
    form=AuthorForm, can_delete=False, extra=2, min_num=1
)


class RolesForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        required=True,
    )
    roles = forms.MultipleChoiceField(
        label="Roles",
        widget=CheckboxSelectMultiple,
        required=False,
        choices=[(role, role) for role in ("collaborator", "administrator")],
    )
    prefix = "role"

    def __init__(self, *args, **kwargs):
        roles = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)

        if roles:
            self.fields["email"].initial = roles["email"]
            self.fields["roles"].initial = roles["roles"]


RoleFormset = forms.formset_factory(
    form=RolesForm, can_delete=False, extra=2, min_num=1
)


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
        self.model = kwargs.pop("model")
        label = kwargs.pop("label", "Request DOI")
        force_disable = kwargs.pop("force_disable", False)
        super(ZenodoPublishForm, self).__init__(*args, **kwargs)
        doi_field = self.fields["request_doi"]
        doi_field.disabled = self._has_doi() or force_disable
        if self._has_doi():
            doi_field.label = "Published as {}".format(
                trovi.parse_contents_urn(self.model["contents"]["urn"])["id"]
            )
        else:
            doi_field.label = label

    def get_initial_for_field(self, field, field_name):
        if field_name == "artifact_version_id":
            return self.model["slug"]
        elif field_name == "request_doi":
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
        return _version_is_zenodo(self.model)


def _version_is_zenodo(version):
    return trovi.parse_contents_urn(version["contents"]["urn"])["provider"] == "zenodo"


class BaseZenodoPublishFormset(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        artifact_versions = kwargs.pop("artifact_versions")
        if not artifact_versions:
            raise ValueError("artifact_versions must provided")
        self.artifact_versions = artifact_versions
        self.latest_published_version = -1
        for i, version in enumerate(artifact_versions):
            if _version_is_zenodo(version):
                self.latest_published_version = i

        kwargs["initial"] = [{} for _ in artifact_versions]
        super(BaseZenodoPublishFormset, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        """Pass the linked artifact version model through to the nested form."""
        future_version_published = index < self.latest_published_version
        return {
            "model": self.artifact_versions[index],
            # Prevent publishing versions behind the latest published version
            "force_disable": future_version_published,
            "label": (
                "(cannot request DOI for past versions)"
                if future_version_published
                else None
            ),
        }

    @property
    def cleaned_data(self):
        """Override cleaned_data to ignore forms with empty data."""
        return [x for x in super(BaseZenodoPublishFormset, self).cleaned_data if x]


ZenodoPublishFormset = forms.formset_factory(
    ZenodoPublishForm, formset=BaseZenodoPublishFormset, extra=0
)


class RequestDaypassForm(forms.Form):
    name = forms.CharField()
    email = forms.CharField(disabled=True, required=False)
    institution = forms.CharField()
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": "Reason for request"}),
    )


class ReviewDaypassForm(forms.Form):
    status = forms.ChoiceField(required=True, choices=DaypassRequest.STATUS)

    def clean(self):
        data = self.cleaned_data
        if data.get("status", None) == DaypassRequest.STATUS_PENDING:
            raise forms.ValidationError("You must set a status")
