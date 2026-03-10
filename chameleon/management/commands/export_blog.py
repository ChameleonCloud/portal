from django.core.management.base import BaseCommand
from djangocms_blog.models import Post
import yaml


class Command(BaseCommand):
    """
    Exports blog posts to markdown files with YAML front matter for migration to hugo.
    """

    def handle(self, *args, **kwargs):
        for post in Post.objects.all():
            front_matter = {
                "title": post.get_title(),
                "date": str(post.date_published),
                "slug": post.slug,
                "categories": [t.name for t in post.categories.all()],
                "featured": "featured" in [t.name for t in post.categories.all()],
                "abstract": post.abstract.strip(),
                "authors": [post.author.get_full_name()] if post.author else [],
                "subtitle": post.safe_translation_getter("subtitle", any_language=True),
                "image": post.get_image_full_url() if post.get_image_full_url() else "",
                "hide_image": True,
            }
            # only export published posts
            if post.date_published:
                filename = f"{post.date_published.date()}-{post.slug}.md"
                with open(f"/project/export/{filename}", "w") as f:
                    f.write("---\n")
                    f.write(yaml.dump(front_matter))
                    f.write("---\n\n")
                    f.write(post.post_text)
