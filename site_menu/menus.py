from django.core.urlresolvers import reverse

from menu import Menu, MenuItem

def profile_title(request):
    """
    Personalized account profile menu
    """
    name = request.user.get_full_name() or request.user
    return 'Hello, %s' % name

"""
Main Menu
"""
doc_children = (
    MenuItem( 'Overview', reverse( 'documentation.views.display_doc'), ),
    MenuItem( 'User Guides', reverse( 'documentation.views.display_doc', args=['user-guides']), ),
)

Menu.add_item( 'main',
    MenuItem(
        'Documentation',
        reverse( 'documentation.views.display_doc'),
        weight = 0,
        children = doc_children
    )
)

Menu.add_item( 'main',
    MenuItem(
        'About',
        reverse( 'github_content.views.about' ),
    )
)

Menu.add_item( 'main',
    MenuItem(
        'News',
        reverse( 'github_content.views.news' ),
    )
)

Menu.add_item( 'main',
    MenuItem(
        'Talks',
        reverse( 'github_content.views.talks' ),
    )
)

"""
User Menu
"""
menu_children = (
    MenuItem(
        'Dashboard',
        reverse( 'chameleon.views.dashboard' ),
        check = lambda request: request.user.is_authenticated(),
    ),
    MenuItem(
        'Log Out',
        reverse( 'django.contrib.auth.views.logout' ),
        check = lambda request: request.user.is_authenticated(),
    ),
)

profile_item = MenuItem(
    profile_title,
    '/user',
    children = menu_children,
    check = lambda request: request.user.is_authenticated(),
)

Menu.add_item( 'user', profile_item )

menu_children = (
    MenuItem( 'Log In', reverse( 'django.contrib.auth.views.login' ) ),
    MenuItem( 'Register', reverse( 'tas.views.register' ) ),
    MenuItem( 'Help', reverse( 'djangoRT.views.ticketcreateguest' ) ),
)

Menu.add_item( 'user',
    MenuItem(
        'Log In',
        reverse( 'django.contrib.auth.views.login' ),
        children = menu_children,
        check=lambda request: not request.user.is_authenticated()
    )
)

"""
Dashboard Menu
"""

Menu.add_item(
    'user_dashboard',
    MenuItem(
        'Dashboard',
        reverse( 'chameleon.views.dashboard' ),
        check = lambda request: request.user.is_authenticated(),
    )
)

Menu.add_item(
    'user_dashboard',
    MenuItem(
        'Projects',
        reverse( 'projects.views.user_projects' ),
        check = lambda request: request.user.is_authenticated(),
    )
)

Menu.add_item(
    'user_dashboard',
    MenuItem(
        'FutureGrid@Chameleon',
        reverse( 'projects.views.lookup_fg_projects' ),
        check = lambda request: request.user.is_authenticated(),
    )
)

Menu.add_item(
    'user_dashboard',
    MenuItem(
        'Help Desk',
        reverse( 'djangoRT.views.mytickets' ),
        check = lambda request: request.user.is_authenticated(),
    )
)

Menu.add_item(
    'user_dashboard',
    MenuItem(
        'Profile',
        reverse( 'tas.views.profile' ),
        check = lambda request: request.user.is_authenticated(),
    )
)
