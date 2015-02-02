from menus.base import NavigationNode
from cms.menu_bases import CMSAttachMenu
from menus.menu_pool import menu_pool
from django.utils.translation import ugettext_lazy as _

class TASMenu(CMSAttachMenu):

    name = _('TASMenu')

    def get_nodes(self, request):
        nodes = []

        greeting = 'Hello, {0}'.format(request.user.get_full_name() or request.user) if request.user.is_authenticated() else 'Log in'
        title = '<i class="fa fa-user hidden-xs hidden-md hidden-lg"></i><span class="hidden-sm">{0}</span>'
        n = NavigationNode(title.format(greeting), "/user/", 'user')
        nodes.append(n)

        n = NavigationNode(_('Log in'), "/login/", 'user_login', 'user', attr={'visible_for_authenticated':False})
        nodes.append(n)

        n = NavigationNode(_('Register'), "/register/", 'user_register', 'user', attr={'visible_for_authenticated':False})
        nodes.append(n)

        n = NavigationNode(_('Dashboard'), "/user/dashboard/", 'dashboard', 'user', attr={'visible_for_anonymous':False})
        nodes.append(n)

        n = NavigationNode(_('Dashboard'), "/user/dashboard/", 'dashboard_home', 'dashboard', attr={'visible_for_anonymous':False})
        nodes.append(n)

        n = NavigationNode(_('Profile'), "/user/profile/", 'profile', 'dashboard', attr={'visible_for_anonymous':False})
        nodes.append(n)

        n = NavigationNode(_('Experiment'), "https://horizon.chameleon.tacc.utexas.edu/", 3, 'user', attr={'visible_for_anonymous':False})
        nodes.append(n)

        n = NavigationNode(_('Log out'), "/logout/", 4, 'user', attr={'visible_for_anonymous':False})
        nodes.append(n)

        return nodes

menu_pool.register_menu(TASMenu)
