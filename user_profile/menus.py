from django.core.urlresolvers import reverse

from menu import Menu, MenuItem

def profile_title(request):
    """
    Personalized account profile menu
    """
    name = request.user.get_full_name() or request.user
    return 'Hello, %s' % name

Menu.add_item('user', MenuItem(profile_title,
                               reverse('user_profile.views.profile'),
                               check=lambda request: request.user.is_authenticated()))

Menu.add_item('user', MenuItem('Log out',
                               reverse('django.contrib.auth.views.logout'),
                               check=lambda request: request.user.is_authenticated()))
"""
Menu.add_item('user', MenuItem('Register',
                               reverse('django.contrib.auth.views.registration'),
                               check=lambda request: not request.user.is_authenticated()))
"""

Menu.add_item('user', MenuItem('Log in',
                               reverse('django.contrib.auth.views.login'),
                               check=lambda request: not request.user.is_authenticated()))
