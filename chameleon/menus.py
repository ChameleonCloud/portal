from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

Menu.add_item("main", MenuItem("Test",
                               reverse("chameleon.views.home"),
                               weight=9))
