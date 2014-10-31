from django.core.urlresolvers import reverse
from menu import Menu, MenuItem


about_children = (
    MenuItem("Schedule",
            reverse("about.views.schedule")),
    MenuItem("Team",
            reverse("about.views.teamMembers")),
)

Menu.add_item("main", MenuItem("About",
                               reverse("about.views.about"),
                               weight=2,
                               children=about_children))
