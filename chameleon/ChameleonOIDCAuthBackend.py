import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

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
        """Override to search for users by username and not email."""
        username = claims.get("preferred_username")
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

        return user

    def update_user(self, user, claims):
        """Override to update the username field and set first/last name."""
        LOG.debug("Updating user from keycloak with claims: {0}".format(claims))

        # We allow Keycloak to override the email set in Portal
        user.email = claims.get("email", "")
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.save()

        return user
