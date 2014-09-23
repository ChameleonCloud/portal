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
Menu.add_item("main", MenuItem("News",
                               reverse("news.views.index"),
                               weight=3,
                               children=news_children))

#Menu.add_item("main", MenuItem("News",
#                               reverse("news.views.index"),
#                               weight=3))

# Project menu

# Project == Allocation? Allocations can have extensions and supplements?

Menu.add_item("main", MenuItem("Administration",
                               "/admin/",
                               weight=7,
                               check=lambda request: request.user.is_superuser))
