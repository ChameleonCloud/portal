from django import forms

from .models import Label


class LabelForm(forms.Form):
    """
    Form to allow search on the index page
    """
    # Text input search
    search = forms.CharField(required=False)

    # Labels to allow user to choose from
    label_options = [(str(label.id), label.label)
                     for label in Label.objects.all()]
    labels = forms.MultipleChoiceField(label='Labels', required=False,
                                       choices=label_options)

    # Boolean and vs or search style
    is_or = forms.BooleanField(required=False)
