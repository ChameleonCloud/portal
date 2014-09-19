from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

# this file should be split up and pieces moved to the right apps

# don't really need a home menu
Menu.add_item("main", MenuItem("Home",
                               reverse("chameleon.views.home"),
                               weight=1))

news_children = (
    MenuItem("Announcements",
             reverse("news.views.announcements")),
    MenuItem("Events",
             reverse("news.views.events")),
    MenuItem("Outages",
             reverse("news.views.outages")),
)

# the css isn't right for the news_children
#Menu.add_item("main", MenuItem("News",
#                               weight=3))
#                               reverse("news.views.index"),
#                               children=news_children))

Menu.add_item("main", MenuItem("News",
                               reverse("news.views.index"),
                               weight=3))

# Project menu

# Project == Allocation? Allocations can have extensions and supplements?

Menu.add_item("main", MenuItem("Help",
                               "/helpdesk/",
                               weight=5))

Menu.add_item("main", MenuItem("Admin",
                               "/admin/",
                               weight=6,
                               check=lambda request: request.user.is_superuser))

Menu.add_item("main", MenuItem("Login",
                               "/accounts/login/",
                               weight=10,
                               check=lambda request: not request.user.is_authenticated()))

Menu.add_item("main", MenuItem("Logout",
                               "/accounts/logout/",
                               weight=10,
                               check=lambda request: request.user.is_authenticated()))
