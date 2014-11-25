from django import forms
from pytas.pytas import client as TASClient

RESEARCH = 0
STARTUP = 2
PROJECT_TYPES = (
    ('', 'Choose One'),
    (RESEARCH, 'Research'),
    (STARTUP, 'Startup'),
)

FIELDS_CHOICES = (('', 'Choose One'),)
tas = TASClient()
fields = tas.fields()
for f in fields:
    FIELDS_CHOICES = FIELDS_CHOICES + ((f['id'], f['name']),)
    if f['children']:
        for c in f['children']:
            FIELDS_CHOICES = FIELDS_CHOICES + ((c['id'], '--- ' + c['name']),)
            if c['children']:
                for g in c['children']:
                    FIELDS_CHOICES = FIELDS_CHOICES + ((g['id'], '--- --- ' + g['name']),)

class ProjectCreateForm( forms.Form ):
    title = forms.CharField(
        label='Title',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Research into how...'}),
    )
    description = forms.CharField(
        label='Abstract',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    typeId = forms.IntegerField(
        label='Type',
        required=True,
        widget=forms.Select( choices=PROJECT_TYPES ),
        help_text='Please select the project type.',
    )
    fieldId = forms.IntegerField(
        label='Field of Science',
        required=True,
        widget=forms.Select( choices=FIELDS_CHOICES ),
        initial=3,
        help_text='Please indicate a primary field of science for this research',
    )

class ProjectEditForm( forms.Form ):
    title = forms.CharField(
        label='Title',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Research into how...'}),
    )
    description = forms.CharField(
        label='Abstract',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'We propose to...'}),
    )
    fieldId = forms.IntegerField(
        label='Field of Science',
        required=True,
        widget=forms.Select( choices=FIELDS_CHOICES ),
        initial=3,
        help_text='Please indicate a primary field of science for this research',
    )

class AllocationEditForm( forms.Form ):
    computeRequested = forms.IntegerField(
        label='SUs Requested',
        required=True,
        help_text='Enter the number of SUs you would like to request',
    )
    justification = forms.CharField(
        label='Justification',
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Provide a brief justification for the use of this resource'}),
    )

class ProjectAddUserForm( forms.Form ):
    username = forms.CharField(
        label='Add a User to Project',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username of User'}),
    )
