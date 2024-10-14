from cms.menu_bases import CMSAttachMenu
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menus.base import NavigationNode, Modifier
from menus.menu_pool import menu_pool


class UserMenu(CMSAttachMenu):
    name = _("User Menu")

    def get_nodes(self, request):
        nodes = []
        menu_id = 0

        #
        # Top menu
        #
        # menu_id += 1
        # n = NavigationNode(_('Help Desk'), reverse('djangoRT:ticketcreateguest'), menu_id, attr={'visible_for_authenticated': False, 'class': 'navbar-btn-alt'})
        # nodes.append(n)
        menu_id += 1
        n = NavigationNode(
            _("Help Desk"),
            reverse("djangoRT:ticketcreateguest"),
            menu_id,
            attr={"visible_for_anonymous": True, "class": "navbar-btn-alt"},
        )
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(
            "Log in",
            reverse("login"),
            menu_id,
            attr={"visible_for_authenticated": False, "class": "navbar-btn-alt"},
        )
        nodes.append(n)

        #
        # Dropdown menu
        #
        menu_id += 1
        greeting = (
            "&nbsp;{0}&nbsp;".format(request.user.username)
            if request.user.is_authenticated
            else ""
        )
        title = '<i class="fa fa-user"></i><span class="hidden-sm">{0}</span>'
        n = NavigationNode(
            title.format(greeting),
            "/user/",
            menu_id,
            attr={"visible_for_anonymous": False},
        )
        nodes.append(n)

        root_id = menu_id

        menu_id += 1
        n = NavigationNode(_("Dashboard"), reverse("dashboard"), menu_id, root_id)
        nodes.append(n)

        dashboard_id = menu_id

        menu_id += 1
        n = NavigationNode(_("Profile"), reverse("tas:profile"), menu_id, root_id)
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_("Log out"), reverse("logout"), menu_id, root_id)
        nodes.append(n)

        #
        # Dashboard sub-menu
        #
        menu_id += 1
        n = NavigationNode(_("Dashboard"), reverse("dashboard"), menu_id, dashboard_id)
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(
            _("Projects"), reverse("projects:user_projects"), menu_id, dashboard_id
        )
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_("Outages"), reverse("outage_list"), menu_id, dashboard_id)
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(
            _("Help Desk"), reverse("djangoRT:mytickets"), menu_id, dashboard_id
        )
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(_("Profile"), reverse("tas:profile"), menu_id, dashboard_id)
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(
            _("Webinars"),
            "https://www.chameleoncloud.org/learn/webinars/",
            menu_id,
            dashboard_id,
        )
        nodes.append(n)

        menu_id += 1
        n = NavigationNode(
            _("Publications"), reverse("projects:publications"), menu_id, dashboard_id
        )
        nodes.append(n)

        if request.session.get("has_legacy_account", False):
            menu_id += 1
            n = NavigationNode(
                _("Migrate account"),
                reverse("federation_migrate_account"),
                menu_id,
                dashboard_id,
            )
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
        reverse_id = node.attr.get("reverse_id")

        if reverse_id and reverse_id in ["share"]:
            node.attr["class"] = "new"

        if node.children:
            [self.mark_new(child) for child in node.children]


menu_pool.register_modifier(NewContentModifier)
menu_pool.register_menu(UserMenu)
