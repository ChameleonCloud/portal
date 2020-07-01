from django import forms
from pytas.http import TASClient
import re
import logging
logger = logging.getLogger(__name__)

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


def check_password_policy(user, password, confirm_password):
    """
    Checks the password for meeting the minimum password policy requirements:
    * Must be a minimum of 8 characters in length
    * Must contain characters from at least three of the following: uppercase letters,
      lowercase letters, numbers, symbols
    * Must NOT contain the username or the first or last name from the profile

    Returns:
        A boolean value indicating if the password meets the policy,
        An error message string or None
    """
    if password != confirm_password:
        return False, 'The password provided does not match the confirmation.'

    if len(password) < 8:
        return False, 'The password provided is too short. Please review the password criteria.'

    char_classes = 0
    for cc in ['[a-z]', '[A-Z]', '[0-9]', '[^a-zA-Z0-9]']:
        if re.search(cc, password):
            char_classes += 1

    if char_classes < 3:
        return False, 'The password provided does not meet the complexity requirements.'

    pwd_without_case = password.lower()
    if user['username'].lower() in pwd_without_case:
        return False, 'The password provided must not contain parts of your name or username.'

    if user['firstName'].lower() in pwd_without_case or user['lastName'].lower() in pwd_without_case:
        return False, 'The password provided must not contain parts of your name or username.'

    return True, None

class RecoverUsernameForm(forms.Form):
    email = forms.CharField(label='Enter Your Email Address', required=True)

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
                                            'Passwords must meet the following criteria:<ul>'
                                            '<li>Must not contain your username or parts of '
                                            'your full name;</li><li>Must be a minimum of 8 characters '
                                            'in length;</li><li>Must contain characters from at least '
                                            'three of the following: uppercase letters, '
                                            'lowercase letters, numbers, symbols</li></ul>')

    def clean(self):
        cleaned_data = self.cleaned_data
        username = cleaned_data.get('username')

        try:
            tas = TASClient()
            user = tas.get_user(username=username)
        except:
            self.add_error('username', 'The username provided does not match an existing user.')
            raise forms.ValidationError('The username provided does not match an existing user.')

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        valid, error_message = check_password_policy(user, password, confirm_password)
        if not valid:
            self.add_error('password', error_message)
            self.add_error('confirm_password', '')
            raise forms.ValidationError(error_message)


class UserProfileForm(forms.Form):
    firstName = forms.CharField(label='First name')
    lastName = forms.CharField(label='Last name')
    email = forms.EmailField()
    phone = forms.CharField()
    institutionId = forms.ChoiceField(label='Institution', choices=(), error_messages={'invalid': 'Please select your affiliated institution'})
    departmentId = forms.ChoiceField(label='Department', choices=(), required=False)
    title = forms.ChoiceField(label='Position/Title', choices=USER_PROFILE_TITLES)
    countryId = forms.ChoiceField(label='Country of residence', choices=(), error_messages={'invalid': 'Please select your Country of residence'})
    citizenshipId = forms.CharField(label='Country of citizenship', widget=forms.HiddenInput(), error_messages={'invalid': 'Please select your Country of citizenship'})

    def __init__(self, *args, **kwargs):
        is_federated = kwargs.pop('is_federated', False)
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['institutionId'].choices = get_institution_choices()
        data = self.data or self.initial
        if (data is not None and 'institutionId' in data and data['institutionId']):
            self.fields['departmentId'].choices = get_department_choices(data['institutionId'])
        if is_federated:
            for field in self.fields:
                self.fields[field].widget.attrs['readonly'] = True
        self.fields['countryId'].choices = get_country_choices()
        self.fields['citizenshipId'].widget.attrs['readonly'] = True


class TasUserProfileAdminForm(forms.Form):
    """
    Admin Form for TAS User Profile. Adds a field to trigger a password reset
    on the User's behalf.
    """
    firstName = forms.CharField(label="First name")
    lastName = forms.CharField(label="Last name")
    email = forms.EmailField()
    phone = forms.CharField()
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
    phone = forms.CharField()
    institutionId = forms.ChoiceField(label='Institution', choices=(), error_messages={'invalid': 'Please select your affiliated institution'})
    departmentId = forms.ChoiceField(label='Department', choices=(), required=False)
    institution = forms.CharField(label='Institution name',
                                      help_text='If your institution is not listed, please provide the name of the institution as it should be shown here.',
                                      required=False,
                                      )
    title = forms.ChoiceField(label='Position/Title', choices=USER_PROFILE_TITLES)
    countryId = forms.ChoiceField(label='Country of residence', choices=(), error_messages={'invalid': 'Please select your Country of residence'})
    citizenshipId = forms.ChoiceField(label='Country of citizenship', choices=(), error_messages={'invalid': 'Please select your Country of citizenship'})

    username = forms.RegexField(label='Username',
                               help_text='Usernames must be 3-8 characters in length, start with a letter, and can contain only lowercase letters, numbers, or underscore.',
                               regex='^[a-z][a-z0-9_]{2,7}$')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    confirmPassword = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['institutionId'].choices = get_institution_choices()
        self.fields['institutionId'].choices += (('-1', 'My Institution is not listed'),)

        data = self.data or self.initial
        if (data is not None and 'institutionId' in data and data['institutionId']):
            self.fields['departmentId'].choices = get_department_choices(data['institutionId'])

        self.fields['countryId'].choices = get_country_choices()
        self.fields['citizenshipId'].choices = get_country_choices()

    def clean(self):
        username = self.cleaned_data.get('username')
        firstName = self.cleaned_data.get('firstName')
        lastName = self.cleaned_data.get('lastName')
        password = self.cleaned_data.get('password')
        confirmPassword = self.cleaned_data.get('confirmPassword')


        if username and firstName and lastName and password and confirmPassword:
            valid, error_message = check_password_policy(self.cleaned_data,
                                                         password,
                                                         confirmPassword)
            if not valid:
                self.add_error('password', error_message)
                self.add_error('confirmPassword', '')
                raise forms.ValidationError(error_message)
