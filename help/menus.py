
from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

help_children = (
    MenuItem("Knowledge Base",
             "/helpdesk/kb/"),
    MenuItem("Ticketing System",
             "/helpdesk/tickets/",
             check=lambda request: request.user.is_authenticated()),
)

Menu.add_item("main", MenuItem("Help",
                               "/helpdesk/",
                               weight=5,
                               children=help_children))
