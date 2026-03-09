from django.core.management.base import BaseCommand
from projects.membership import append_project_membership_event
from projects.util import get_user_by_reference
from util.keycloak_client import KeycloakClient, UserAttributes


class Command(BaseCommand):
    """
    Management command to initialize group events for all users based on their current project memberships.
    This is intended to be run once after the group events feature is implemented, to backfill
    existing users with appropriate group events for their current memberships. These events are backfilled
    with the action "add_backdate" to indicate that they are being added after the fact, and the date of the
    event will be set to the current date.
    """

    help = "Backdate group events for users without any based on their current project memberships."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without writing any changes",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]

        print("Fetching all users from Keycloak...")
        keycloak_client = KeycloakClient()
        kc_user_map = keycloak_client.get_all_users()
        for kc_user in kc_user_map.values():
            print(
                f"Processing user {kc_user['username']} with existing events {kc_user['attributes'].get(UserAttributes.GROUP_EVENTS)}"
            )
            charge_codes = keycloak_client._get_charge_codes_for_kc_id(kc_user["id"])
            update_args = {}
            for charge_code in charge_codes:
                update_args["group_events"] = append_project_membership_event(
                    kc_user, charge_code, "add_backdate", check_duplicates=True
                )
                kc_user["attributes"][UserAttributes.GROUP_EVENTS] = update_args[
                    "group_events"
                ]

            # print summary of updates
            print(
                f"Would update user {kc_user['username']} with group events: {update_args.get('group_events')}"
            )
            if not self.dry_run:
                # It is not optimal to refetch the user here, but it's OK for just initial migration
                portal_user = get_user_by_reference(
                    keycloak_id=kc_user["id"],
                    username=kc_user["username"],
                    email=kc_user.get("email"),
                )
                if portal_user:
                    keycloak_client.update_user(portal_user, **update_args)
                else:
                    print(
                        f"Could not find portal user for Keycloak user {kc_user['username']}"
                    )
