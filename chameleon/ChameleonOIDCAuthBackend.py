from mozilla_django_oidc.auth import OIDCAuthenticationBackend
import logging

logger = logging.getLogger('auth')

class ChameleonOIDCAB(OIDCAuthenticationBackend):

    def authenticate(self, request, **kwargs):
        login = super(ChameleonOIDCAB, self).authenticate(request, **kwargs)
        if login:
            access_token = request.session.get('oidc_access_token','')
            user_info = self.get_userinfo(access_token, None, None)
            logger.info(user_info)
            request.session['is_federated'] = True
            request.session['is_pi'] = ('principal_investigator' in user_info.get('realm_access.roles', []))
        return login

    def create_user(self, claims):
        logger.debug('Creating user from keycloak with claims: {0}'.format(claims))
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
