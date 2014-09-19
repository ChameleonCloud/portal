from django.core.urlresolvers import reverse
from menu import Menu, MenuItem

doc_children = (
    MenuItem("Geting Started",
            "/documentation/getting_started.html"),
    MenuItem("FAQ",
            "/documentation/faq.html"),
    MenuItem("User Guides",
            "/documentation/user-guides/"),
    MenuItem("Acceptable Usage Policy",
            "/documentation/acceptable-usage.html"),
)

Menu.add_item("main", MenuItem("Documentation",
                               "/documentation/",
                               weight=4,
                               children=doc_children))
