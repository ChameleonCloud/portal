from django.contrib import admin

from .models import TicketCategories


class TicketCategoriesAdmin(admin.ModelAdmin):
    list_display = ("category_display_name", "category_field_name")


admin.site.register(TicketCategories, TicketCategoriesAdmin)
