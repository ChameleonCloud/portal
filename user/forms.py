
import ldap

from django.contrib.auth.forms import PasswordChangeForm

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


