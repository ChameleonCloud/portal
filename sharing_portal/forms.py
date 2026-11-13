from django import forms
from django.forms import widgets
from django.forms.utils import pretty_name

from projects.models import Project
from trovi_launcher import credentials
from util.project_allocation_mapper import ProjectAllocationMapper

from .models import DaypassRequest
from . import trovi

import logging

LOG = logging.getLogger(__name__)


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
            for project in mapper.get_user_projects(request.user, to_pytas_model=False)
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
        artifact_versions = kwargs.pop("artifact_versions", [])
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


class GenericLaunchForm(forms.Form):
    """Site and project, plus arguments for the provisioner.

    The artifact's arguments are the initial values, and any it names that
    aren't fields below get a field of their own.
    """

    ARGUMENT_FIELDS = {bool: forms.BooleanField, int: forms.IntegerField}
    KEY_PREFIXES = ("ssh-", "ecdsa-", "sk-")
    FIELDSETS = [
        ("Context", ["site", "project"]),
        ("Lease", ["node_type", "lease_duration_hours", "lease_id"]),
        ("Instance", ["image"]),
        ("Access", ["ssh_public_key"]),
    ]

    site = forms.ChoiceField()
    project = forms.ChoiceField()
    image = forms.CharField(
        label="Disk image", initial="CC-Ubuntu24.04", required=False
    )
    node_type = forms.CharField(
        required=False,
        help_text=(
            "The kind of node to reserve, such as compute_skylake. The hardware "
            "catalog lists the node types at each site."
        ),
    )
    lease_duration_hours = forms.IntegerField(
        label="Lease length (hours)", min_value=1, required=False
    )
    lease_id = forms.CharField(
        label="Existing lease ID",
        required=False,
        help_text=(
            "Optional. Launch on a lease you already made; it must be active or "
            "start within 15 minutes. The length then comes from the lease."
        ),
    )
    ssh_public_key = forms.CharField(
        label="SSH public key",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Added to the node so you can log in as cc.",
    )

    def __init__(self, request, arguments, *args, **kwargs):
        super().__init__(*args, initial=arguments, **kwargs)
        self.fields["site"].choices = [(site, site) for site in credentials.sites()]
        mapper = ProjectAllocationMapper(request)
        self.fields["project"].choices = [
            (project["chargeCode"], project.get("nickname") or project["chargeCode"])
            for project in mapper.get_user_projects(request.user, fetch_balance=False)
            if any(a["status"].lower() == "active" for a in project["allocations"])
        ]
        extra = [name for name in arguments if name not in self.fields]
        for name in extra:
            field = self.ARGUMENT_FIELDS.get(type(arguments[name]), forms.CharField)
            self.fields[name] = field(
                label=name.replace("_", " ").capitalize(), required=False
            )
        self.order_fields(["site", "project", *extra])

    @classmethod
    def label_for(cls, name):
        field = cls.base_fields.get(name)
        return field and field.label or pretty_name(name)

    def fieldsets(self):
        """Return (legend, bound fields) pairs; the artifact's own come last."""
        fieldsets = [
            (legend, [self[name] for name in names]) for legend, names in self.FIELDSETS
        ]
        named = {name for _, names in self.FIELDSETS for name in names}
        if extra := [field for field in self if field.name not in named]:
            fieldsets.append(("Artifact settings", extra))
        return fieldsets

    def clean_ssh_public_key(self):
        key = self.cleaned_data["ssh_public_key"].strip()
        parts = key.split()
        if "\n" in key or len(parts) < 2 or not parts[0].startswith(self.KEY_PREFIXES):
            raise forms.ValidationError("Enter a single OpenSSH public key.")
        return key

    def clean(self):
        data = super().clean()
        if not data.get("lease_id") and not (
            data.get("node_type") and data.get("lease_duration_hours")
        ):
            raise forms.ValidationError(
                "Set a node type and lease length, or an existing lease ID."
            )
        return data

    def arguments(self):
        return {
            name: value
            for name, value in self.cleaned_data.items()
            if name not in ("site", "project") and value not in ("", None)
        }
