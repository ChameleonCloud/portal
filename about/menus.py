from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

Menu.add_item("main", MenuItem("About",
                               reverse("about.views.about"),
                               weight=2))
