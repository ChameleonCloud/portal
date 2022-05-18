from django import forms
from . import models


class WebinarRegistrantForm(forms.ModelForm):
    class Meta:
        model = models.WebinarRegistrant
        fields = ["user", "webinar"]
        widgets = {"user": forms.HiddenInput(), "webinar": forms.HiddenInput()}


class WebinarAdminForm(forms.ModelForm):
    class Meta:
        model = models.Webinar
        fields = [
            "name",
            "description",
            "registration_open",
            "registration_closed",
            "registration_limit",
            "start_date",
            "end_date",
        ]


class WebinarRegistrantAdminForm(forms.ModelForm):
    class Meta:
        model = models.WebinarRegistrant
        fields = ["user", "webinar"]
