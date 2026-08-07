from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from chameleon.models import KeycloakUser

import logging

LOG = logging.getLogger("auth")


class ChameleonOIDCAB(OIDCAuthenticationBackend):
    def authenticate(self, request, **kwargs):
        return super().authenticate(request, **kwargs)

    def filter_users_by_claims(self, claims):
        """
        Override to search for users by stable Keycloak 'sub' claim instead of username.
        Falls back to username for legacy users if no user is found by sub.
        """
        sub = claims.get("sub")
        username = claims.get("preferred_username")

        # Try to match by sub first
        if sub:
            users = self.UserModel.objects.filter(keycloak_user__sub=sub)
            if users.exists():
                return users

        # Fallback for legacy users before sub was set
        if username:
            return self.UserModel.objects.filter(username__iexact=username)

        return self.UserModel.objects.none()

    def get_username(self, claims):
        """Override default behavior to use preferred_username as username."""
        return claims.get("preferred_username")

    def create_user(self, claims):
        """Override to set first and last name."""
        LOG.debug("Creating user from keycloak with claims: {0}".format(claims))

        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        sub = claims.get("sub")
        if sub:
            KeycloakUser.objects.get_or_create(user=user, sub=sub)

        return user

    def update_user(self, user, claims):
        """Override to update the username field and set first/last name."""
        LOG.debug("Updating user from keycloak with claims: {0}".format(claims))

        # We allow Keycloak to override the email set in Portal
        user.email = claims.get("email", "")
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")

        # If the preferred_username claim has changed, update the username
        # field as well, but only if it doesn't conflict with another user.
        new_username = claims.get("preferred_username")
        if (
            new_username
            and user.username != new_username
            and not self.UserModel.objects.filter(username__iexact=new_username)
            .exclude(pk=user.pk)
            .exists()
        ):
            LOG.info(
                "Updating username for user %s to %s",
                user.username,
                new_username,
            )
            user.username = new_username

        user.save()

        keycloak_user = KeycloakUser.objects.filter(user=user).first()
        sub = claims.get("sub")
        if not keycloak_user:
            KeycloakUser.objects.get_or_create(user=user, sub=sub)
        elif not keycloak_user.sub:
            keycloak_user.sub = sub
            keycloak_user.save()
        elif keycloak_user.sub != sub:
            # Keycloak should prevent this from ever happening
            LOG.warning(
                "User %s already linked to a different Keycloak sub (%s != %s)",
                user.username,
                keycloak_user.sub,
                sub,
            )
        return user
