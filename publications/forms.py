from django import forms

class AddBibtexPublicationForm(forms.Form):
    # related_allocations = forms.MultipleChoiceField(
    #     label='Related Allocations',
    #     required=False,
    #     widget=forms.CheckboxSelectMultiple,
    # )

    project_id = forms.CharField(widget=forms.HiddenInput())

    bibtex_string = forms.CharField(
        label='Publication(s) in BibTeX format',
        help_text='Please list any publication citations and related allocation.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': '@article{...'}),
    )

    # def __init__(self, *args, **kwargs):
    #     self.ALLOCATIONS_LIST = kwargs.pop('ALLOCATIONS_LIST')
    #     super(AddBibtexPublicationForm, self).__init__(*args, **kwargs)
    #     self.fields['related_allocations'].choices = self.ALLOCATIONS_LIST
