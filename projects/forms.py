import logging
from textwrap import dedent

import bibtexparser
from django import forms
from django.core.urlresolvers import reverse_lazy
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
    supplemental_details = forms.CharField(
        label="Resource Justification",
        help_text=(
            "Provide supplemental detail on how you intend to use Chameleon to "
            "accomplish your research goals. This text will not be publicly "
            "viewable and may include details that you do not wish to publish."
        ),
        required=True,
        widget=forms.Textarea(attrs={"placeholder": "Resource Justification"}),
    )
    funding_source = forms.CharField(
        label="Source(s) of funding",
        help_text=(
            "If the proposed research is related to a funded grant or has pending "
            "support, please include funding agency name(s) and grant name(s)."
        ),
        required=False,
        widget=forms.Textarea(),
    )
    fieldId = forms.ChoiceField(
        label="Field of Science",
        choices=(),
        initial="45",
        help_text="Please indicate a primary field of science for this research.",
    )
    typeId = forms.ChoiceField(
        label="Type",
        choices=(),
        initial="",
        help_text="Please indicate a project type.",
    )
    accept_project_terms = forms.BooleanField(
        label="I agree to abide by Chameleon Acceptable Use Policies.",
        help_text=get_accept_project_terms_help_text_lazy(),
    )

    def __init__(self, *args, **kwargs):
        if "request" in kwargs:
            request = kwargs["request"]
            del kwargs["request"]
            super(ProjectCreateForm, self).__init__(*args, **kwargs)
            mapper = ProjectAllocationMapper(request)
            self.fields["fieldId"].choices = mapper.get_fields_choices()
            self.fields["typeId"].choices = mapper.get_project_types_choices()
        else:
            logger.error("Couldn't get field or type list.")


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


class EditTypeForm(forms.Form):
    typeId = forms.ChoiceField(
        label="",
        choices=(),
        initial="",
        help_text="",
        required=True,
    )

    def is_valid(self, request):
        return super(EditTypeForm, self).is_valid()

    def __init__(self, *args, **kwargs):
        if "request" in kwargs:
            request = kwargs["request"]
            del kwargs["request"]
            super(EditTypeForm, self).__init__(*args, **kwargs)
            mapper = ProjectAllocationMapper(request)
            self.fields["typeId"].choices = mapper.get_project_types_choices()
        else:
            logger.error("Couldn't get type list.")


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
    supplemental_details = forms.CharField(
        label="Resource Justification",
        help_text=(
            "Please provide an update on the use of your current allocation - any "
            "success stories, presentations, or just a general update on the "
            "progress of your research on Chameleon. This is helpful "
            "for us as we communicate with NSF regarding the value Chameleon is "
            "bringing to the research community."
        ),
        required=True,
        widget=forms.Textarea(),
    )
    funding_source = forms.CharField(
        label="Source(s) of funding",
        help_text=(
            "If the proposed research is related to a funded grant or has pending "
            "support, please include funding agency name(s) and grant name(s)."
        ),
        required=False,
        widget=forms.Textarea(),
    )
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
        label="Publication(s) in BibTeX format",
        help_text=(
            "Please enter publications in BibTex Format. If you can provide "
            "a link, please enter in note or howpublished using the url package."
        ),
        required=True,
        widget=forms.Textarea(attrs={"placeholder": "@article{..."}),
    )

    def is_valid(self):
        if not super(AddBibtexPublicationForm, self).is_valid():
            return False

        bib_database = bibtexparser.loads(self.cleaned_data["bibtex_string"])
        logger.debug(bib_database.entries)

        if not bib_database.entries:
            self.add_error(
                "bibtex_string",
                (
                    "Invalid formatting or missing one of required fields, "
                    "publication/journal/booktitle, title, year, author in BibTeX "
                    "entry"
                ),
            )
            return False

        return True
