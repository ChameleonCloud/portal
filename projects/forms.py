import logging
from textwrap import dedent

import bibtexparser
from django import forms
from django.forms import BaseFormSet
from django.forms import formset_factory
from django.urls import reverse_lazy
from django.utils.functional import lazy
from util.project_allocation_mapper import ProjectAllocationMapper

from .models import Project

logger = logging.getLogger("projects")


def get_accept_project_terms_help_text():
    user_terms_url = reverse_lazy(
        "tc_view_specific_version_page", args=["user-terms", "1.00"]
    )
    project_terms_url = reverse_lazy(
        "tc_view_specific_version_page", args=["project-terms", "1.00"]
    )
    return dedent(
        f"""
    Please review the Chameleon <a href="{user_terms_url}">User Terms of Use</a>
    and <a href="{project_terms_url}">Project Lead Terms of Use</a>.
    """
    )


get_accept_project_terms_help_text_lazy = lazy(get_accept_project_terms_help_text, str)


class ProjectCreateForm(forms.Form):
    title = forms.CharField(
        label="Title",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Research into how..."}),
    )
    nickname = forms.CharField(
        label="Project Nickname",
        max_length="50",
        help_text=(
            "Provide a nickname to identify your project across the Chameleon "
            "Infrastructure"
        ),
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Project Nickname"}),
    )
    tagId = forms.ChoiceField(
        label="Tag",
        choices=(),
        initial="",
        help_text="Please choose the research area that is "
        "most similar to the research you will conduct.",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        if "request" in kwargs:
            request = kwargs["request"]
            del kwargs["request"]
            super(ProjectCreateForm, self).__init__(*args, **kwargs)
            mapper = ProjectAllocationMapper(request)
            self.fields["tagId"].choices = mapper.get_project_tags_choices()
        else:
            logger.error("Couldn't get field or tag list.")


class EditNicknameForm(forms.Form):
    nickname = forms.CharField(
        label="",
        max_length="50",
        help_text="",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Project Nickname"}),
    )

    def is_valid(self, request):
        valid = super(EditNicknameForm, self).is_valid()
        if not valid:
            return valid
        self.cleaned_data["nickname"] = self.cleaned_data["nickname"].strip()
        if not self.cleaned_data["nickname"]:
            return False

        return not Project.objects.filter(
            nickname=self.cleaned_data["nickname"]
        ).exists()


class EditTagForm(forms.Form):
    tagId = forms.ChoiceField(
        label="",
        choices=(),
        initial="",
        help_text="Please choose the research area that is "
        "most similar to the research you will conduct.",
        required=True,
    )

    def is_valid(self, request):
        return super(EditTagForm, self).is_valid()

    def __init__(self, *args, **kwargs):
        if "request" in kwargs:
            request = kwargs["request"]
            del kwargs["request"]
            super(EditTagForm, self).__init__(*args, **kwargs)
            mapper = ProjectAllocationMapper(request)
            self.fields["tagId"].choices = mapper.get_project_tags_choices()
        else:
            logger.error("Couldn't get tag list.")


class EditPIForm(forms.Form):
    pi_username = forms.CharField(
        label="",
        max_length="500",
        help_text="",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "PI username"}),
    )


class FundingForm(forms.Form):
    id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False,
    )
    agency = forms.CharField(
        label="Agency",
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter Agency"}
        ),
        error_messages={"required": "Please enter agency"},
    )
    award = forms.CharField(
        label="Award #",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter Award Number"}
        ),
        required=False,
    )
    grant_name = forms.CharField(
        label="Grant Name",
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter Grant Name"}
        ),
        error_messages={"required": "Please enter grant name"},
    )


class FundingFormSet(BaseFormSet):
    def clean(self):
        # check if the last form is empty
        last_form_cleaned_data = self.forms[-1].cleaned_data
        last_form_cleaned_data = {k: v for k, v in last_form_cleaned_data.items() if v}

        if last_form_cleaned_data:
            self.forms[-1].add_error(
                None, "Please use the plus button to add the funding!"
            )
        else:
            self.forms.pop(-1)

        return super(FundingFormSet, self).clean()


FundingFormset = formset_factory(FundingForm, formset=FundingFormSet, extra=0)


class AllocationCreateForm(forms.Form):
    description = forms.CharField(
        label="Abstract (~200 words)",
        help_text=(
            "An application for a project has to include a description of the "
            "research or education project to be performed using the testbed and "
            "the type of resources needed. It should address the following "
            "questions: What are the research challenges or educational objectives "
            "of the project? How are they relevant to cloud computing research? "
            "Why are they important? What types of experiments or educational "
            "activities will be carried out? Please, make sure that the abstract "
            "is self-contained; eventually it may be published on the Chameleon "
            "website."
        ),
        required=True,
        widget=forms.Textarea(attrs={"placeholder": "We propose to..."}),
    )
    justification = forms.CharField(
        label="Resource Justification",
        help_text=(
            "If this is the first allocation request for the project, "
            "please provide supplemental detail on how you intend "
            "to use Chameleon to accomplish your research goals. For "
            "extending and recharging, please provide an update on the use "
            "of your current allocation - any success stories, or just a "
            "general update on the progress of your research on Chameleon. "
            "This is helpful for us as we communicate with NSF regarding "
            "the value Chameleon is bringing to the research community. "
            "This text will not be publicly viewable and may include details "
            "that you do not wish to publish."
        ),
        required=True,
        widget=forms.Textarea(),
    )
    publication_up_to_date = forms.BooleanField(
        label="The publications are up-to-date",
        help_text=(
            "Is your publications up-to-date? View your "
            '<a href="/user/projects/publications/" target="_blank">publication list</a>, '
            "and make sure it's up-to-update."
        ),
        required=True,
    )


class ConsentForm(forms.Form):
    accept_project_terms = forms.BooleanField(
        label="I agree to abide by Chameleon Acceptable Use Policies",
        help_text=get_accept_project_terms_help_text_lazy(),
    )


class ProjectAddUserForm(forms.Form):
    user_ref = forms.CharField(
        label="Add a User to Project",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Username or email"}),
    )


class AddBibtexPublicationForm(forms.Form):
    project_id = forms.CharField(widget=forms.HiddenInput())
    bibtex_string = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"placeholder": "@article{..."}),
    )
    bibtex_error = ""

    mandatory_fields = ["title", "year", "author"]

    def parse_bibtex(self, bibtex_string):
        try:
            return bibtexparser.loads(bibtex_string)
        except bibtexparser.bibdatabase.UndefinedString as e:
            self.bibtex_error = f"{e} not a valid string"
            return None

    def is_valid(self):
        if not super().is_valid():
            return False

        bib_database = self.parse_bibtex(self.cleaned_data["bibtex_string"])
        if bib_database and bib_database.entries:
            missing_fields = []
            for entry in bib_database.entries:
                missing = [field for field in self.mandatory_fields if field not in entry]
                missing_fields.extend(missing)

            if missing_fields:
                self.bibtex_error = f"Missing mandatory fields: {', '.join(missing_fields)}"
                return False
        else:
            return False
        return True


class ProjectAddBulkUserForm(forms.Form):
    username_csv = forms.CharField(
        label="Usernames or emails",
        widget=forms.Textarea(attrs={"placeholder": "Usernames one per line"}),
    )
