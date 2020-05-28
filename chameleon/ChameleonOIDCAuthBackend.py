from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from chameleon.models import UserProperties
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
        props = UserProperties(user=user)
        if('principal_investigator' in claims.get('realm_access.roles', [])):
            logger.debug('found principal_investigator status ' + \
                str('principal_investigator' in claims.get('realm_access.roles', [])) + ' for user: ' + user.username)
            props.is_pi_eligible = True
        props.save()
        return user

    def update_user(self, user, claims):
        try:
            props = UserProperties.objects.get(user=user)
        except UserProperties.DoesNotExist:
            props = UserProperties(user=user)
            logger.debug('found principal_investigator status ' + \
                str('principal_investigator' in claims.get('realm_access.roles', [])) + ' for user: ' + user.username)
            props.is_pi_eligible = ('principal_investigator' in claims.get('realm_access.roles', []))
        props.save()
        logger.debug('Updating user from keycloak with claims: {0}'.format(claims))
        user.username = claims.get('preferred_username', '')
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.save()
        return user
