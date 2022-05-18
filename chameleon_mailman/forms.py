from django.forms import ModelForm
from .models import MailmanSubscription


class MailmanSubscriptionForm(ModelForm):
    class Meta:
        model = MailmanSubscription
        exclude = ["user"]
