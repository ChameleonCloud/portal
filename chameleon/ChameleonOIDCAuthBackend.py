from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from chameleon.models import UserProperties
import logging

logger = logging.getLogger('auth')

class ChameleonOIDCAB(OIDCAuthenticationBackend):
    def create_user(self, claims):
        logger.debug('Creating user from keycloak with claims: {0}'.format(claims))
        email = claims.get('email')
        username = claims.get('preferred_username', '')
        user = self.UserModel.objects.create_user(username, email)
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()
        props = UserProperties(user=user)
        props.is_pi = ('principal_investigator' in claims.get('realm_access.roles', []))
        props.save()
        return user

    def update_user(self, user, claims):
        logger.debug('Updating user from keycloak with claims: {0}'.format(claims))
        user.username = claims.get('preferred_username', '')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()

        try:
            props = UserProperties.objects.get(user=user)
        except UserProperties.DoesNotExist:
            props = UserProperties(user=user)
        props.is_pi = ('principal_investigator' in claims.get('realm_access.roles', []))
        props.save()

        return user
