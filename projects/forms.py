from django import forms
from pytas.http import TASClient
from django.core.urlresolvers import reverse_lazy
from django.utils.functional import lazy


RESEARCH = 0
STARTUP = 2
PROJECT_TYPES = (
    ('', 'Choose One'),
    (RESEARCH, 'Research'),
    (STARTUP, 'Startup'),
)


def get_fields_choices():
    choices = (('', 'Choose One'),)
    tas = TASClient()
    fields = tas.fields()
    for f in fields:
        choices = choices + ((f['id'], f['name']),)
        if f['children']:
            for c in f['children']:
                choices = choices + ((c['id'], '--- ' + c['name']),)
                if c['children']:
                    for g in c['children']:
                        choices = choices + ((g['id'], '--- --- ' + g['name']),)
    return choices


def get_accept_project_terms_help_text():
    user_terms_url = reverse_lazy('terms:tc_view_specific_version_page',
                                    args=['user-terms', '1.00'])
    project_terms_url = reverse_lazy('terms:tc_view_specific_version_page',
                                    args=['project-terms', '1.00'])
    text = 'Please review the Chameleon <a href="%s">User Terms of Use</a> and ' \
            '<a href="%s">Project Lead Terms of Use</a>.' % \
            (user_terms_url, project_terms_url)
    return text

get_accept_project_terms_help_text_lazy = lazy(get_accept_project_terms_help_text, str)

class ProjectCreateForm( forms.Form ):
    title = forms.CharField(
        label='Title',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Research into how...'}),
    )
    description = forms.CharField(
        label='Abstract',
        help_text='Your project abstract may be publicly viewable on the Chameleon website.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    supplemental_details = forms.CharField(
        label='Resource justification',
        help_text='Provide details for how you intend to use Chameleon to accomplish '
                  'your research goals. This text will not be publicly viewable.',
        required=True,
        widget=forms.Textarea(),
    )
    funding_source = forms.CharField(
        label='Source(s) of funding',
        help_text='If the proposed research is related to a funded grant or has pending '
                  'support, please include funding agency name(s) and grant name(s).',
        required=False,
        widget=forms.Textarea()
    )
    fieldId = forms.ChoiceField(
        label='Field of Science',
        choices=(),
        initial='3',
        help_text='Please indicate a primary field of science for this research',
    )
    accept_project_terms = forms.BooleanField(
        label='I agree to abide by Chameleon Acceptable Use Policies',
        help_text=get_accept_project_terms_help_text_lazy(),
    )

    def __init__(self, *args, **kwargs):
        super(ProjectCreateForm, self).__init__(*args, **kwargs)
        self.fields['fieldId'].choices = get_fields_choices()

class AllocationCreateForm(forms.Form):
    description = forms.CharField(
        label='Abstract',
        help_text='Your project abstract may be publicly viewable on the '
                  'Chameleon website.',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    supplemental_details = forms.CharField(
        label='Request Justification',
        help_text='Provide a brief summary of what was achieved under the previous '
                  'request, including references to papers and/or other artifacts.',
        required=True,
        widget=forms.Textarea(),
    )
    funding_source = forms.CharField(
        label='Source(s) of funding',
        help_text='If the proposed research is related to a funded grant or has pending '
                  'support, please include funding agency name(s) and grant name(s).',
        required=False,
        widget=forms.Textarea()
    )
    accept_project_terms = forms.BooleanField(
        label='I agree to abide by Chameleon Acceptable Use Policies',
        help_text=get_accept_project_terms_help_text_lazy(),
    )


# class ProjectEditForm( forms.Form ):
#     title = forms.CharField(
#         label='Title',
#         required=True,
#         widget=forms.TextInput(attrs={'placeholder': 'Research into how...'}),
#     )
#     description = forms.CharField(
#         label='Abstract',
#         required=True,
#         widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
#     )
#     fieldId = forms.ChoiceField(
#         label='Field of Science',
#         choices=(),
#         initial=3,
#         help_text='Please indicate a primary field of science for this research',
#     )

#     def __init__(self, *args, **kwargs):
#         super(ProjectEditForm, self).__init__(*args, **kwargs)
#         self.fields['fieldId'].choices = get_fields_choices()

# class AllocationEditForm( forms.Form ):
#     computeRequested = forms.IntegerField(
#         label='SUs Requested',
#         required=True,
#         help_text='Enter the number of SUs you would like to request',
#     )
#     justification = forms.CharField(
#         label='Request Justification',
#         required=True,
#         widget=forms.Textarea(attrs={
#                'placeholder': 'Provide a brief summary of what was achieved under the '
#                               'previous request, including pointers to papers and '
#                               'other artifacts'
#                }),
#     )

class ProjectAddUserForm( forms.Form ):
    username = forms.CharField(
        label='Add a User to Project',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username of User'}),
    )
