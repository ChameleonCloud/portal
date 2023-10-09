import logging

from captcha.fields import ReCaptchaField, ReCaptchaV3
from django import forms
from django.core.validators import validate_email

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
    project_id = forms.CharField(
        widget=forms.TextInput(),
        label="Project ID",
        max_length=100,
        required=False,
        help_text="Which project are you using,  if applicable (e.g. CHI-123456).",
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
        super(BaseTicketForm, self).__init__(*args, **kwargs)
        self.fields["category"].choices = get_ticket_categories()


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
    captcha = ReCaptchaField(widget=ReCaptchaV3, label="")


class ReplyForm(forms.Form):
    """Ticket Reply form."""

    reply = forms.CharField(required=True, widget=forms.Textarea(), label="Enter Reply")
    attachment = forms.FileField(required=False)


class CloseForm(forms.Form):
    """Ticket Close form."""

    reply = forms.CharField(
        required=True, widget=forms.Textarea(), label="Enter Close Comment"
    )
