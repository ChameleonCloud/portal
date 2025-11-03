from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from chameleon.models import KeycloakUser

import logging

LOG = logging.getLogger("auth")


class ChameleonOIDCAB(OIDCAuthenticationBackend):
    def authenticate(self, request, **kwargs):
        login = super().authenticate(request, **kwargs)
        if login:
            try:
                access_token = request.session.get("oidc_access_token")
                if not access_token:
                    raise ValueError(
                        (
                            "Failed to store access token! Is "
                            "OIDC_STORE_ACCESS_TOKEN enabled?"
                        )
                    )
                user_info = self.get_userinfo(access_token, None, None)
                linked_identities = user_info.get("linked_identities")
                if linked_identities is None:
                    raise ValueError(
                        "Failed to get linked_identities claim from user info"
                    )
                if "tacc" in linked_identities:
                    request.session["has_legacy_account"] = True
            except:
                LOG.exception(
                    (
                        "Failed to fetch federated identities for "
                        f"{request.user.username}"
                    )
                )
            request.session["is_federated"] = True
        return login

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
        user = super().update_user(user, claims)

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
                user.username, keycloak_user.sub, sub
            )
        return user
