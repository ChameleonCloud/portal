from django.core.urlresolvers import reverse
from menu import Menu, MenuItem


#Menu.add_item("main", MenuItem("Documentation",
#                               reverse("documentation.views.index")))
Menu.add_item("main", MenuItem("Documentation",
                               "/documentation/",
                               weight=4))
