
import ldap

from django.contrib.auth.forms import PasswordChangeForm

from django.forms import Form, ModelForm, ValidationError
from django.forms import CharField, Textarea

from user.models import ChameleonUser, UserProfile

# don't need this - using a mix in with ChameleonUser
class ChameleonPasswordChangeForm(PasswordChangeForm):
    # override save to write to LDAP
    def save_disable(self, commit=True):
        print("#### newpassword1 is %s" % self.cleaned_data['new_password1'])
        
        # no need to self.user.set_password() or self.user.save()
        #   set_password() saves the hashed password

        print("user dn: %s" % self.user.ldap_user._get_user_dn())
        print("old password: %s" % self.cleaned_data['old_password'])
        conn = self.user.ldap_user._get_connection()
        conn.simple_bind_s(self.user.ldap_user._get_user_dn(),self.cleaned_data['old_password'])
        conn.passwd_s(self.user.ldap_user._get_user_dn(),
                      None,
                      self.cleaned_data['new_password1'])
        #conn.passwd_s(self.user.ldap_user._get_user_dn(),
        #              self.cleaned_data['old_password'],
        #              self.cleaned_data['new_password1'])
        conn.unbind_s()

        #self._bind_as(self.settings.BIND_DN, self.settings.BIND_PASSWORD,sticky=True)
        #self._get_connection().simple_bind_s(force_str(bind_dn),force_str(bind_password))

        return self.user


class ChameleonUserForm(ModelForm):
    class Meta:
        model = ChameleonUser
        fields = ["first_name","last_name","email","username"]

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise ValidationError(u'first name is required.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise ValidationError(u'last name is required.')
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError(u'email address is required.')
        if ChameleonUser.objects.filter(email=email).count() > 0:
            raise ValidationError(u'This email address is already registered.')
        return email

class UserProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        exclude = ["user","status","roles"]
        #fields = []

class ApproveUserForm(Form):
    deny_reason = CharField(max_length=2000,
                            required=False,
                            widget=Textarea,
                            help_text="the reason why the account request was denied (optional)")
