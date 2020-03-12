from menus.base import NavigationNode, Modifier
from cms.menu_bases import CMSAttachMenu
from menus.menu_pool import menu_pool
from django.utils.translation import ugettext_lazy as _

class UserMenu(CMSAttachMenu):

    name = _('User Menu')

    def get_nodes(self, request):
        nodes = []

        menu_id = 1

        n = NavigationNode('Log in', "/login/", menu_id, attr={'visible_for_authenticated':False, 'class':'navbar-btn-alt'})
        nodes.append(n)

        # root node
        menu_id += 1
        root_id = menu_id
        greeting = '&nbsp;{0}&nbsp;'.format(request.user.username ) if request.user.is_authenticated() else ''
        title = '<i class="fa fa-user"></i><span class="hidden-sm">{0}</span>'
        n = NavigationNode(title.format(greeting), "/user/", menu_id)
        nodes.append(n)

        # drop down
        menu_id += 1
        n = NavigationNode(_('Register'), "/user/register/", menu_id, root_id, attr={'visible_for_authenticated':False})
        nodes.append(n)

        menu_id += 1
        dashboard_id = menu_id
        n = NavigationNode(_('Dashboard'), "/user/dashboard/", menu_id, root_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Help Desk'), "/user/help/ticket/new/guest/", menu_id, root_id, attr={'visible_for_authenticated':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Help Desk'), "/user/help/", menu_id, root_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Log out'), "/logout/", menu_id, root_id, attr={'visible_for_anonymous':False})
        nodes.append(n)


        # user section dashboard sub-menu
        menu_id += 1
        n = NavigationNode(_('Dashboard'), "/user/dashboard/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Projects'), "/user/projects/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        # menu_id += 1
        # n = NavigationNode(_('FutureGrid@Chameleon'), "/user/projects/futuregrid/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        # nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Outages'), "/user/outages/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Help Desk'), "/user/help/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Profile'), "/user/profile/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Webinars'), "/user/webinar/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_('Publications'), "/user/publications/", menu_id, dashboard_id, attr={'visible_for_anonymous':False})
        nodes.append(n)

        return nodes


class NewContentModifier(Modifier):
    """
    This modifier tags certain pages (by title) as "new", so additional
    UI can be shown to highlight them in the navbar.
    """
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        # only do something when the menu has already been cut
        if post_cut:
            [self.mark_new(node) for node in nodes]

        return nodes

    def mark_new(self, node):
        reverse_id = node.attr.get('reverse_id')

        if reverse_id and reverse_id in ['jupyter', 'kvm', 'share']:
            node.attr['class'] = 'new'

        if node.children:
            [self.mark_new(child) for child in node.children]

menu_pool.register_modifier(NewContentModifier)
menu_pool.register_menu(UserMenu)
