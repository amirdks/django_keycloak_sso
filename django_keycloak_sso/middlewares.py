from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from jose import JWTError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from django_keycloak_sso.sso.authentication import CustomUser
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient


class KeycloakAuthentication(BaseAuthentication):
    def authenticate(self, request):
        keycloak_klass = KeyCloakConfidentialClient()
        token = keycloak_klass.get_token(request, 'access_token')
        # token = keycloak_klass.get_token_from_header(request)
        if not token:
            return None
        try:
            payload = keycloak_klass.decode_token(token)
            user = CustomUser(
                is_authenticated=True,
                payload=payload
            )
            return user, None
        except KeyCloakConfidentialClient.KeyCloakException as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")


class KeycloakMiddleware(MiddlewareMixin):
    def process_request(self, request):
        keycloak_klass = KeyCloakConfidentialClient()
        token = keycloak_klass.get_token(request, 'access_token')
        if token:
            try:
                payload = keycloak_klass.decode_token(token)
                request.user = CustomUser(
                    is_authenticated=True,
                    payload=payload
                )
            except KeyCloakConfidentialClient.KeyCloakException as e:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
