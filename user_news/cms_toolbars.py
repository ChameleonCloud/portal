from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER, ADMINISTRATION_BREAK
from cms.toolbar.items import Break, SubMenu
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


@toolbar_pool.register
class UserNewsToolbar(CMSToolbar):
    def populate(self):
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)

        position = admin_menu.get_alphabetical_insert_position(_("User News"), SubMenu)

        if not position:
            position = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK) + 1
            admin_menu.add_break("custom-break", position=position)

        user_news_menu = admin_menu.get_or_create_menu(
            "user_news-menu", _("User News ..."), position=position
        )

        url = reverse("admin:user_news_news_changelist")
        user_news_menu.add_sideframe_item("List News", url=url)

        url = reverse("admin:user_news_news_add")
        user_news_menu.add_modal_item(_("Add News"), url=url)

        user_news_menu.add_break()

        url = reverse("admin:user_news_event_changelist")
        user_news_menu.add_sideframe_item("List Events", url=url)

        url = reverse("admin:user_news_event_add")
        user_news_menu.add_modal_item(_("Add Event"), url=url)

        user_news_menu.add_break()

        url = reverse("admin:user_news_outage_changelist")
        user_news_menu.add_sideframe_item("List Outages", url=url)

        url = reverse("admin:user_news_outage_add")
        user_news_menu.add_modal_item(_("Add Outage"), url=url)
        pass

    def post_template_populate(self):
        pass

    def request_hook(self):
        pass
