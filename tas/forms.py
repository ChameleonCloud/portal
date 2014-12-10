from django import forms
from pytas.pytas import client as TASClient
import re

ELIGIBLE = 'Eligible'
INELIGIBLE = 'Ineligible'
PI_ELIGIBILITY = (
    ('', 'Choose One'),
    (ELIGIBLE, ELIGIBLE),
    (INELIGIBLE, INELIGIBLE),
)

COUNTRIES = (('', 'Choose One'))

INSTITUTIONS = (('', 'Choose One'))
inst = tas.institutions()
for i in inst:
    INSTITUTIONS += ((i['id'], i['name']))



def _password_policy( password ):
    """
    Checks the password for meeting the minimum password policy requirements;

    Must be a minimum of 8 characters in length
    Must contain characters from at least three of the following: uppercase letters, lowercase letters, numbers, symbols
    """
    if len( password ) < 8:
        return False

    char_classes = 0
    for cc in ['[a-z]', '[A-Z]', '[0-9]', '[^a-zA-Z0-9]']:
        if re.search( cc, password ):
            char_classes += 1

    if char_classes < 3:
        return False

    return True

class PasswordResetRequestForm( forms.Form ):
    username = forms.CharField( label='Enter Your Chameleon Username', required=True )

class PasswordResetConfirmForm( forms.Form ):
    username = forms.CharField( label='Enter Your Chameleon Username', required=True )
    code = forms.CharField( label='Reset Code', required=True  )
    password = forms.CharField( widget=forms.PasswordInput, label='Password', required=True )
    confirm_password = forms.CharField( widget=forms.PasswordInput, label='Confirm Password', required=True, help_text='Passwords must meet the following criteria: Must not contain your account name or parts of your full name; Must be a minimum of 8 characters in length; Must contain characters from at least three of the following: uppercase letters, lowercase letters, numbers, symbols' )

    def clean( self ):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get( 'password' )
        confirm_password = cleaned_data.get( 'confirm_password' )

        if password and confirm_password:
            if password != confirm_password:
                self.add_error( 'password', 'The password provided does not match the confirmation' )
                self.add_error( 'confirm_password', '' )
                raise forms.ValidationError( 'The password provided does not match the confirmation' )

class UserRegistrationForm( forms.Form ):
    firstName = forms.CharField( label='First Name', required=True )
    lastName = forms.CharField( label='Last Name', required=True )
    email = forms.EmailField( label='Email Address', required=True )
    institutionId = forms.CharField( label='Institution', required=True )
    countryId = forms.CharField( label='Country of Residence', required=True )
    citizenshipId = forms.CharField( label='Country of Citizenship', required=True )
    piEligibility =
    username = forms.CharField( label='Username', required=True )
    password = forms.CharField( widget=forms.PasswordInput, label='Password', required=True )
    confirmPassword = forms.CharField( widget=forms.PasswordInput, label='Confirm Password', required=True )

    def clean( self ):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get( 'password' )
        confirmPassword = cleaned_data.get( 'confirmPassword' )

        if password and confirmPassword:
            if password != confirmPassword:
                self.add_error( 'password', 'The password provided does not match the confirmation' )
                self.add_error( 'confirmPassword', '' )
                raise forms.ValidationError( 'The password provided does not match the confirmation' )

            if not _password_policy( password ):
                self.add_error( 'password', 'The password provided does not satisfy the password complexity requirements' )
                self.add_error( 'confirmPassword', '' )
                raise forms.ValidationError( 'The password provided does not satisfy the password complexity requirements' )
