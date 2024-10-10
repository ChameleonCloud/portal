from django.contrib import admin
from .models import Comment


class CommentAdmin(admin.ModelAdmin):
    list_display = ["created_date", "post", "author", "text"]


admin.site.register(Comment, CommentAdmin)
