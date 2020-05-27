from mozilla_django_oidc.auth import OIDCAuthenticationBackend
import logging

logger = logging.getLogger('auth')

class ChameleonOIDCAB(OIDCAuthenticationBackend):
    def create_user(self, claims):
        logger.debug('Creating user from keycloak with claims: {0}'.format(claims))
        if self.get_settings('OIDC_USERNAME_ALGO', None):
            return super(ChameleonOIDCAB, self).create_user(claims)
        email = claims.get('email')
        username = claims.get('preferred_username', '')
        user = self.UserModel.objects.create_user(username, email)
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()
        return user

    def update_user(self, user, claims):
        logger.debug('Updating user from keycloak with claims: {0}'.format(claims))
        user.username = claims.get('preferred_username', '')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()
        return user
        