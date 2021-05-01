import logging

from captcha.fields import ReCaptchaField, ReCaptchaV2Checkbox, ReCaptchaV3
from django import forms
from django.core.validators import validate_email

from .models import TicketCategories

logger = logging.getLogger(__name__)

# This was pulled from : https://docs.djangoproject.com/en/1.7/ref/forms/validation/
class MultiEmailField(forms.Field):
    def to_python(self, value):
        """ Normalize data to a list of strings. """

        # Return an empty list if no input was given.
        if not value:
            return []
        return value.split(",")

    def validate(self, value):
        """ Check if value consists only of valid emails. """

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
        "be sure to provide your project name and the details of your problem, "
        "including your username and the UUID of the instance or lease in "
        "question if applicable."
    )

    first_name = forms.CharField(
        widget=forms.TextInput(), label="First name", max_length=100, required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(), label="Last name", max_length=100, required=True
    )
    email = forms.EmailField(widget=forms.EmailInput(), label="Email", required=True)
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

    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


class ReplyForm(forms.Form):
    """Ticket Reply form."""

    reply = forms.CharField(required=True, widget=forms.Textarea(), label="Enter Reply")
    attachment = forms.FileField(required=False)


class CloseForm(forms.Form):
    """Ticket Close form."""

    reply = forms.CharField(
        required=True, widget=forms.Textarea(), label="Enter Close Comment"
    )
