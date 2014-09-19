from django.contrib import admin
from person.models import ChameleonRole,Institution,Person

admin.site.register(Person)
admin.site.register(Institution)
admin.site.register(ChameleonRole)
