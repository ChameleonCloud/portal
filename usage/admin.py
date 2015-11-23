from django.contrib import admin
from .models import Downtime

class DowntimeAdmin(admin.ModelAdmin):
	list_display = ('queue', 'nodes_down', 'start', 'end')
	list_filter = ['created']
	search_fields = ['queue']

admin.site.register(Downtime, DowntimeAdmin)