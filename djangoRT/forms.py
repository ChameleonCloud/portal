import logging

from django_recaptcha.fields import ReCaptchaField, ReCaptchaV3
from django import forms
from django.core.validators import validate_email

from projects.models import Project
from util.keycloak_client import KeycloakClient

from .models import TicketCategories

logger = logging.getLogger(__name__)


# This was pulled from : https://docs.djangoproject.com/en/1.7/ref/forms/validation/
class MultiEmailField(forms.Field):
    def to_python(self, value):
        """Normalize data to a list of strings."""

        # Return an empty list if no input was given.
        if not value:
            return []
        return value.split(",")

    def validate(self, value):
        """Check if value consists only of valid emails."""

        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)

        for email in value:
            validate_email(email.strip())


def get_ticket_categories():
    return (("", "Choose one"),) + tuple(
        TicketCategories.objects.order_by("category_display_name").values_list(
            "category_field_name", "category_display_name"
        )
    )


class BaseTicketForm(forms.Form):
    """Base form class for Tickets."""

    help_text = (
        "In order to help us address your issue in a timely manner, please "
        "describe the expected behavior, and the actual behavior."
    )

    first_name = forms.CharField(
        widget=forms.TextInput(), label="First name", max_length=100, required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(), label="Last name", max_length=100, required=True
    )
    email = forms.EmailField(widget=forms.EmailInput(), label="Email", required=True)
    project_id = forms.ChoiceField(
        label="Project",
        required=True,
        help_text="Which project are you using",
    )
    site = forms.CharField(
        widget=forms.TextInput(),
        label="Site",
        max_length=100,
        required=False,
        help_text="Which site you are using, if applicable (e.g. CHI@TACC).",
    )
    lease_id = forms.CharField(
        widget=forms.TextInput(),
        label="Lease ID",
        max_length=100,
        required=False,
        help_text="Your lease ID, if applicable (e.g. 123e4567-e89b-12d3-a456-426614174000)",
    )
    instance_id = forms.CharField(
        widget=forms.TextInput(),
        label="Instance ID",
        max_length=100,
        required=False,
        help_text="Your instance ID, if applicable (e.g. 123e4567-e89b-12d3-a456-426614174000)",
    )
    subject = forms.CharField(
        widget=forms.TextInput(), label="Subject", max_length=100, required=True
    )
    category = forms.ChoiceField(required=True)
    problem_description = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": help_text}),
        label="Problem description",
        required=True,
    )
    attachment = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)

        super(BaseTicketForm, self).__init__(*args, **kwargs)
        self.fields["category"].choices = get_ticket_categories()

        initialized_projects = False
        if user:
            keycloak_client = KeycloakClient()
            charge_codes = keycloak_client.get_user_from_portal_user(user)
            if charge_codes:
                projects_qs = Project.objects.filter(charge_code__in=charge_codes)
                self.fields["project_id"].choices = [
                    (
                        f"{p.charge_code} - https://chameleoncloud.org/user/projects/{p.id}/",
                        f"{p.charge_code} - {p.title}",
                    )
                    for p in projects_qs.order_by("charge_code")
                ]
                initialized_projects = True
        if not initialized_projects:
            self.fields["project_id"] = forms.CharField(
                widget=forms.TextInput(), label="Project", max_length=100, required=True
            )


class TicketForm(BaseTicketForm):
    """Authenticated users ticket form.

    Additional "CC" field. This field is not
    provided to anonymous users because it could be used for spam.
    """

    cc = MultiEmailField(
        widget=forms.TextInput(),
        label="CC",
        required=False,
        help_text=(
            "Copy other people on this ticket. Multiple emails should be "
            "comma-separated"
        ),
    )


class TicketGuestForm(BaseTicketForm):
    """Anonymous users ticket form.

    Adds a CAPTCHA to reduce spam submissions.
    """

    # label="" to not show the "Captcha" label in webpage
    captcha = ReCaptchaField(widget=ReCaptchaV3(action="guest_ticket"), label="")
    captcha_answer = forms.IntegerField(label="Math Captcha", required=True)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(TicketGuestForm, self).__init__(*args, **kwargs)

        if request:
            if not self.is_bound:
                # Generate a simple math problem
                import random

                num1 = random.randint(1, 10)
                num2 = random.randint(1, 10)
                question = f"What is {num1} + {num2}?"
                expected_sum = num1 + num2

                # Store the expected sum and question in the session
                request.session["captcha_expected_sum"] = expected_sum
                request.session["captcha_question"] = question

                self.fields["captcha_answer"].label = question
                self.fields["captcha_answer"].widget.attrs[
                    "placeholder"
                ] = "Enter the sum"
            else:
                # If bound, use the stored question for the label so it persists on error
                question = request.session.get("captcha_question", "Math Captcha")
                self.fields["captcha_answer"].label = question

        self.request = request

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get("captcha_answer")
        if self.request:
            expected_sum = self.request.session.get("captcha_expected_sum")
            if expected_sum is None:
                # Session expired or manipulated?
                raise forms.ValidationError("Session expired, please refresh the page.")

            if answer != expected_sum:
                raise forms.ValidationError("Incorrect answer, please try again.")
        return answer


class ReplyForm(forms.Form):
    """Ticket Reply form."""

    reply = forms.CharField(required=True, widget=forms.Textarea(), label="Enter Reply")
    attachment = forms.FileField(required=False)


class CloseForm(forms.Form):
    """Ticket Close form."""

    reply = forms.CharField(
        required=True, widget=forms.Textarea(), label="Enter Close Comment"
    )
