from django import forms
from pytas.http import TASClient
import re
import logging


ELIGIBLE = 'Eligible'
INELIGIBLE = 'Ineligible'
REQUESTED = 'Requested'
PI_ELIGIBILITY = (
    ('', 'Choose One'),
    (ELIGIBLE, ELIGIBLE),
    (INELIGIBLE, INELIGIBLE),
    (REQUESTED, REQUESTED),
)


USER_PROFILE_TITLES = (
    ('', 'Choose one'),
    ('Center Non-Researcher Staff', 'Center Non-Researcher Staff'),
    ('Center Researcher Staff', 'Center Researcher Staff'),
    ('Faculty', 'Faculty'),
    ('Government User', 'Government User'),
    ('Graduate Student', 'Graduate Student'),
    ('High School Student', 'High School Student'),
    ('High School Teacher', 'High School Teacher'),
    ('Industrial User', 'Industrial User'),
    ('Unaffiliated User', 'Unaffiliated User'),
    ('Nonprofit User', 'Nonprofit User'),
    ('NSF Graduate Research Fellow', 'NSF Graduate Research Fellow'),
    ('Other User', 'Other User'),
    ('Postdoctorate', 'Postdoctorate'),
    ('Undergraduate Student', 'Undergraduate Student'),
    ('Unknown', 'Unknown'),
    ('University Non-Research Staff', 'University Non-Research Staff'),
    ('University Research Staff', 'University Research Staff (excluding postdoctorates)'),
)


def get_institution_choices():
    tas = TASClient()
    institutions_list = tas.institutions()
    return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in institutions_list)


def get_department_choices(institutionId):
    tas = TASClient()
    departments_list = tas.get_departments(institutionId)
    return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in departments_list)


def get_country_choices():
    tas = TASClient()
    countries_list = tas.countries()
    return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in countries_list)


class EmailConfirmationForm(forms.Form):
    code = forms.CharField(
            label='Enter Your Verification Code',
            required=True,
            error_messages={
                'required': 'Please enter the verification code you received via email.'
            })

    username = forms.CharField(
            label='Enter Your Chameleon Username',
            required=True)


def _password_policy(password):
    """
    Checks the password for meeting the minimum password policy requirements;

    Must be a minimum of 8 characters in length
    Must contain characters from at least three of the following: uppercase letters, lowercase letters, numbers, symbols
    """
    if len(password) < 8:
        return False

    char_classes = 0
    for cc in ['[a-z]', '[A-Z]', '[0-9]', '[^a-zA-Z0-9]']:
        if re.search(cc, password):
            char_classes += 1

    if char_classes < 3:
        return False

    return True

class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(label='Enter Your Chameleon Username', required=True)

class PasswordResetConfirmForm(forms.Form):
    username = forms.CharField(label='Enter Your Chameleon Username', required=True)
    code = forms.CharField(label='Reset Code', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Password', required=True)
    confirm_password = forms.CharField(
                                    widget=forms.PasswordInput,
                                    label='Confirm Password',
                                    required=True,
                                    help_text=
                                            'Passwords must meet the following criteria: '
                                            'Must not contain your account name or parts of '
                                            'your full name; Must be a minimum of 8 characters '
                                            'in length; Must contain characters from at least '
                                            'three of the following: uppercase letters, '
                                            'lowercase letters, numbers, symbols')

    def clean(self):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('password', 'The password provided does not match the confirmation')
                self.add_error('confirm_password', '')
                raise forms.ValidationError('The password provided does not match the confirmation')

            if not _password_policy(password):
                self.add_error('password', 'The password provided does not satisfy the password complexity requirements')
                self.add_error('confirm_password', '')
                raise forms.ValidationError('The password provided does not satisfy the password complexity requirements')


class UserProfileForm(forms.Form):
    firstName = forms.CharField(label='First name')
    lastName = forms.CharField(label='Last name')
    email = forms.EmailField()
    institutionId = forms.ChoiceField(label='Institution', choices=(), error_messages={'invalid': 'Please select your affiliated institution'})
    departmentId = forms.ChoiceField(label='Department', choices=(), required=False)
    title = forms.ChoiceField(label='Position/Title', choices=USER_PROFILE_TITLES)
    countryId = forms.ChoiceField(label='Country of residence', choices=(), error_messages={'invalid': 'Please select your Country of residence'})
    citizenshipId = forms.ChoiceField(label='Country of citizenship', choices=(), error_messages={'invalid': 'Please select your Country of citizenship'})

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['institutionId'].choices = get_institution_choices()

        data = self.data or self.initial
        if (data is not None and 'institutionId' in data):
            self.fields['departmentId'].choices = get_department_choices(data['institutionId'])

        self.fields['countryId'].choices = get_country_choices()
        self.fields['citizenshipId'].choices = get_country_choices()


class TasUserProfileAdminForm(forms.Form):
    """
    Admin Form for TAS User Profile. Adds a field to trigger a password reset
    on the User's behalf.
    """
    firstName = forms.CharField(label="First name")
    lastName = forms.CharField(label="Last name")
    email = forms.EmailField()
    piEligibility = forms.ChoiceField(
        choices=PI_ELIGIBILITY,
        label="PI Eligibility"
       )
    reset_password = forms.BooleanField(
        required=False,
        label="Reset user's password",
        help_text="Check this box to reset the user's password. The user will be "
            "notified via email with instructions to complete the password reset."
       )


class UserRegistrationForm(forms.Form):
    """
    Except for `institution`, this is the same form as `UserProfileForm`. However,
    due to limited ability to control field order, we cannot cleanly inherit from that form.
    """
    firstName = forms.CharField(label='First name')
    lastName = forms.CharField(label='Last name')
    email = forms.EmailField()
    institutionId = forms.ChoiceField(label='Institution', choices=(), error_messages={'invalid': 'Please select your affiliated institution'})
    departmentId = forms.ChoiceField(label='Department', choices=(), required=False)
    institution = forms.CharField(label='Institution name',
                                      help_text='If your institution is not listed, please provide the name of the institution as it should be shown here.',
                                      required=False,
                                      )
    title = forms.ChoiceField(label='Position/Title', choices=USER_PROFILE_TITLES)
    countryId = forms.ChoiceField(label='Country of residence', choices=(), error_messages={'invalid': 'Please select your Country of residence'})
    citizenshipId = forms.ChoiceField(label='Country of citizenship', choices=(), error_messages={'invalid': 'Please select your Country of citizenship'})

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['institutionId'].choices = get_institution_choices()
        self.fields['institutionId'].choices += (('-1', 'My Institution is not listed'),)

        data = self.data or self.initial
        if (data is not None and 'institutionId' in data):
            self.fields['departmentId'].choices = get_department_choices(data['institutionId'])

        self.fields['countryId'].choices = get_country_choices()
        self.fields['citizenshipId'].choices = get_country_choices()


class UserAccountForm(forms.Form):
    username = forms.RegexField(label='Username',
                               help_text='Usernames must be 3-8 characters in length, start with a letter, and can contain only lowercase letters, numbers, or underscore.',
                               regex='^[a-z][a-z0-9_]{2,7}$')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    confirmPassword = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def clean(self):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get('password')
        confirmPassword = cleaned_data.get('confirmPassword')

        if password and confirmPassword:
            if password != confirmPassword:
                self.add_error('password', 'The password provided does not match the confirmation')
                self.add_error('confirmPassword', '')
                raise forms.ValidationError('The password provided does not match the confirmation')

            if not _password_policy(password):
                self.add_error('password', 'The password provided does not satisfy the password complexity requirements')
                self.add_error('confirmPassword', '')
                raise forms.ValidationError('The password provided does not satisfy the password complexity requirements')
