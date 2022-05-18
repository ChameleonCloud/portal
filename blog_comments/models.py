from django.conf import settings
from django.db import models
from djangocms_blog import models as blogmodels
from django.utils import timezone
from django.utils import html

# Create your models here.


class Comment(models.Model):
    id = models.Model
    # Create your models here.
    post = models.ForeignKey(
        blogmodels.Post,
        on_delete=models.CASCADE,
        related_name="comments",
        related_query_name="comment",
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)
    approved_comment = models.BooleanField(default=False)

    def approve(self):
        self.approved_comment = True
        self.save()
