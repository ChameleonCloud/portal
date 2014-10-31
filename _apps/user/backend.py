
from types import MethodType

import django_auth_ldap.backend
from django.contrib.auth.hashers import check_password

def ldap_check_password(self, password):
    print("#### my check_password ####")
    return check_password(password, self.password)

class LDAPBackend(django_auth_ldap.backend.LDAPBackend):
    def get_user_model(self):
        print("#### ldap backend shim")
        user = super(LDAPBackend,self).get_user_model()
        # inject our method
        #user.check_password = ldap_check_password.__get__(user,user.__class__)
        user.check_password = MethodType(ldap_check_password,user,user.__class__)
        return user

# has a replacement check_password function that checks against ldap
#class LdapUser(AbstractUser):
#    def check_password(self, password):
#        print("#### my check_password ####")
#        User.check_password(self,password)
