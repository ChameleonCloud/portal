from django.core.urlresolvers import reverse

from menu import Menu, MenuItem

def profile_title(request):
    """
    Personalized account profile menu
    """
    name = request.user.get_full_name() or request.user
    return 'Hello, %s' % name

user_children = (
    MenuItem( 'Account Profile', reverse( 'tas.views.profile' ) ),
    MenuItem( 'Log Out', reverse( 'django.contrib.auth.views.logout' ) ),
)

Menu.add_item( 'user',
    MenuItem(
        profile_title,
        reverse( 'tas.views.profile' ),
        children = user_children,
        check = lambda request: request.user.is_authenticated(),
    ),
)

user_children = (
    MenuItem( 'Log In', reverse( 'django.contrib.auth.views.login' ) ),
    MenuItem( 'Register', reverse( 'tas.views.register' ) ),
)

Menu.add_item( 'user',
    MenuItem(
        'Log In',
        reverse( 'django.contrib.auth.views.login' ),
        children = user_children,
        check=lambda request: not request.user.is_authenticated()
    )
)
