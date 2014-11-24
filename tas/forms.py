from django import forms

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
