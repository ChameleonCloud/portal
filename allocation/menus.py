from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

Menu.add_item("main", MenuItem("Allocations",
                               "/allocation/",
                               weight=6,
                               check=lambda request: request.user.is_authenticated()))
