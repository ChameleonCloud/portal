"""
One-time migration: collapse CMS 3.x draft/published page pairs into single pages.

In CMS 3.x, every published page existed as two cms_page rows sharing the same
node_id — one draft and one published copy. CMS 4.x expects exactly one page per
node. This command deletes the redundant higher-id copy for each duplicated node,
along with its associated PageContent, Placeholder, and PageURL rows.

Run once after upgrading to django-cms 4.x. Safe to run multiple times (idempotent).
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count

from cms.models import CMSPlugin, Page, PageContent, Placeholder

logger = logging.getLogger(__name__)


def _delete_plugins_in_placeholders(placeholder_ids):
    """
    Delete all CMSPlugin rows (and their MTI child rows) for the given placeholder IDs.

    Django's ORM delete can't cascade to child tables whose apps are no longer
    installed (aldryn-bootstrap3, djangocms-bootstrap4, cmsplugin-filer, etc.),
    so we query information_schema to discover every FK child table and delete
    from them explicitly before removing the cms_cmsplugin parent rows.
    """
    with connection.cursor() as c:
        ph_sql = ",".join(["%s"] * len(placeholder_ids))
        c.execute(
            f"SELECT id FROM cms_cmsplugin WHERE placeholder_id IN ({ph_sql})",
            placeholder_ids,
        )
        plugin_ids = [row[0] for row in c.fetchall()]

    if not plugin_ids:
        return

    plugin_sql = ",".join(["%s"] * len(plugin_ids))

    with connection.cursor() as c:
        # NULL out self-referential parent_id to break the internal tree dependency
        # (can't delete a parent row while child rows still reference it)
        c.execute(
            f"UPDATE cms_cmsplugin SET parent_id = NULL WHERE id IN ({plugin_sql})",
            plugin_ids,
        )
        # NULL out alias plugin_id references that point into this set
        c.execute(
            f"UPDATE cms_aliaspluginmodel SET plugin_id = NULL"
            f" WHERE plugin_id IN ({plugin_sql})",
            plugin_ids,
        )

        # Find all MTI child tables (cmsplugin_ptr_id FK) — excludes the
        # self-referential parent_id and alias plugin_id cases handled above
        c.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME = 'cms_cmsplugin'
              AND COLUMN_NAME = 'cmsplugin_ptr_id'
            """,
        )
        mti_tables = [row[0] for row in c.fetchall()]

        for table_name in mti_tables:
            c.execute(
                f"DELETE FROM `{table_name}` WHERE cmsplugin_ptr_id IN ({plugin_sql})",
                plugin_ids,
            )

        c.execute(
            f"DELETE FROM cms_cmsplugin WHERE id IN ({plugin_sql})",
            plugin_ids,
        )


class Command(BaseCommand):
    help = "Collapse CMS 3.x draft/published page pairs into single pages for CMS 4.x"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        dupes = (
            Page.objects.values("node_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .order_by("node_id")
        )

        if not dupes.exists():
            self.stdout.write(self.style.SUCCESS("No duplicate node_ids found — nothing to do."))
            return

        self.stdout.write(f"Found {dupes.count()} node_ids with duplicate pages.")

        pc_content_type = ContentType.objects.get(app_label="cms", model="pagecontent")
        deleted_pages = 0

        for dupe in dupes:
            node_id = dupe["node_id"]
            pages = list(Page.objects.filter(node_id=node_id).order_by("id"))
            if len(pages) < 2:
                # Already cleaned up in a previous (partial) run
                continue
            # Keep lowest id (original draft), delete higher-id copies (published copies)
            keep = pages[0]
            to_delete = pages[1:]

            for page in to_delete:
                pcs = PageContent._base_manager.filter(page=page)
                placeholder_ids = list(
                    Placeholder.objects.filter(
                        content_type=pc_content_type,
                        object_id__in=pcs.values_list("id", flat=True),
                    ).values_list("id", flat=True)
                )

                if dry_run:
                    self.stdout.write(
                        f"  [dry-run] node_id={node_id}: would delete Page id={page.id}, "
                        f"{pcs.count()} PageContent(s), {len(placeholder_ids)} Placeholder(s)"
                    )
                    continue

                with transaction.atomic():
                    if placeholder_ids:
                        _delete_plugins_in_placeholders(placeholder_ids)
                        Placeholder.objects.filter(id__in=placeholder_ids).delete()

                    pcs.delete()

                    with connection.cursor() as c:
                        c.execute("DELETE FROM cms_pageurl WHERE page_id = %s", [page.id])
                        # Raw SQL to avoid Page.delete() which calls TreeNode.delete_fast()
                        # and would destroy the entire page tree.
                        c.execute("DELETE FROM cms_page WHERE id = %s", [page.id])

                    deleted_pages += 1
                    logger.info("Deleted duplicate Page id=%s for node_id=%s (kept Page id=%s)", page.id, node_id, keep.id)

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete — no changes made."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Deleted {deleted_pages} duplicate pages."))
