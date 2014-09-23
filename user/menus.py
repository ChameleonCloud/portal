from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

def user_name(request):
    #return "Profile"
    if request.user.first_name:
        return "welcome, %s" % request.user.first_name
    else:
        return "welcome, %s" % request.user.username

#                               reverse("user.views.register"),
#                               "/user/register/",
Menu.add_item("user", MenuItem("Create Account",
                               "/accounts/signup",
                               weight=1,
                               check=lambda request: not request.user.is_authenticated()))

#                               "/accounts/login/",
Menu.add_item("user", MenuItem("Login",
                               "/user/login/",
                               weight=2,
                               check=lambda request: not request.user.is_authenticated()))

Menu.add_item("user", MenuItem(user_name,
                               "/user/profile/",
                               weight=1,
                               check=lambda request: request.user.is_authenticated()))

#                               "/accounts/logout/",
Menu.add_item("user", MenuItem("Logout",
                               "/user/logout/",
                               weight=2,
                               check=lambda request: request.user.is_authenticated()))

