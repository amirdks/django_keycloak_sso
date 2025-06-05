import base64
import datetime
import hashlib
import os
import time
from typing import Type, Optional, Any
from urllib.parse import urlencode

import requests
from django.core.cache import cache
from django.db.models import TextChoices
from django.http import HttpRequest
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _
from jose import exceptions as jose_exceptions
from jose import jwt
from requests import HTTPError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from .helpers import get_settings_value
from .initializer import KeyCloakInitializer

_jwks = None


class KeyCloakBaseManager(KeyCloakInitializer):
    class KeyCloakException(Exception):
        pass

    class KeyCloakNotFoundException(Exception):
        pass

    class KeyCloakGroupRoleChoices(TextChoices):
        MANAGER = "MANAGER", _("Manager")
        ASSISTANT = "ASSISTANT", _("Assistant")
        EMPLOYEE = "EMPLOYEE", _("Employee")

    class KeyCloakClientTypeChoices(TextChoices):
        CONFIDENTIAL = "CONFIDENTIAL", _("Confidential")
        PUBLIC = "PUBLIC", _("Public")

    class KeyCloakPanelTypeChoices(TextChoices):
        ADMIN = "ADMIN", _("Admin")
        USER = "USER", _("User")

    class KeyCloakRequestMethodChoices(TextChoices):
        GET = "GET", _("Get")
        POST = "POST", _("Post")

    class KeyCloakSaveTokenMethodChoices(TextChoices):
        COOKIE = "COOKIE", _("Cookie")
        HEADER = "HEADER", _("Header")

    def __init__(self, save_token_method: str = KeyCloakSaveTokenMethodChoices.HEADER):
        self.save_token_method = get_settings_value('KEYCLOAK_SAVE_TOKEN_METHOD', save_token_method)

    @staticmethod
    def _generate_code_verifier() -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('utf-8')

    @staticmethod
    def _generate_code_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')

    @classmethod
    def validate_enums_value(cls, value: str, enums_class: Type[TextChoices]) -> None:
        if value not in enums_class.values:
            raise cls.KeyCloakException(
                _("Value is not exists in that enums")
            )

    @staticmethod
    def _build_filter_url(*, base_url: str, extra_query_params: dict = None, detail_pk: str | None = None) -> str:
        query_params = {}
        base_url = f'{base_url}/{detail_pk}' if detail_pk else base_url
        if extra_query_params:
            query_params.update(extra_query_params)
        return f"{base_url}?{urlencode(query_params)}" if query_params else base_url

    def _get_headers(self, extra_headers: dict = None) -> dict:
        headers = {
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _get_request_data(
            self,
            *,
            endpoint: str,
            request_method: KeyCloakRequestMethodChoices,
            post_data: dict = None,
            extra_headers: dict = None,
            is_admin: bool = False
    ) -> Any:
        if is_admin:
            url = f"{self.base_admin_url}{endpoint}"
        else:
            url = f"{self.base_panel_url}{endpoint}"
        try:
            response = None
            if request_method == self.KeyCloakRequestMethodChoices.GET:
                headers = self._get_headers(extra_headers=extra_headers)
                response = requests.get(
                    url,
                    headers=headers,
                    verify=False,
                    # verify=get_settings_value('ENVIRONMENT') == 'prod'
                )
            elif request_method == self.KeyCloakRequestMethodChoices.POST:
                response = requests.post(
                    url,
                    data=post_data,
                    headers=self._get_headers(extra_headers=extra_headers),
                    verify=False
                    # verify=get_settings_value('ENVIRONMENT') == 'prod'
                )
            if response is not None:
                response.raise_for_status()
                if response.status_code in (200, 204) and not response.content.strip():
                    return {"detail": "Request successful"}
                return response.json()
        # TODO : fix this dumb handler
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            print(http_err.response.content)
            if http_err.response.status_code == 404:
                raise self.KeyCloakNotFoundException(_("Url or object was not found : 404 error"))
            print(http_err)
            raise self.KeyCloakException(http_err)
        except Exception as err:
            print(err)
            raise self.KeyCloakException(err)

    def send_request(
            self,
            request_type: TextChoices,
            request_type_choices: Type[TextChoices],
            request_method: KeyCloakRequestMethodChoices,
            panel_type: KeyCloakPanelTypeChoices,
            *args,
            **kwargs
    ):
        self.validate_enums_value(panel_type, self.KeyCloakPanelTypeChoices)
        self.validate_enums_value(request_type, request_type_choices)
        self.validate_enums_value(request_method, self.KeyCloakRequestMethodChoices)
        get_data_method = getattr(self, f'_{request_method.lower()}_{request_type.lower()}')
        if not get_data_method or not callable(get_data_method):
            raise self.KeyCloakException("Data get method for keycloak is not valid")
        res = get_data_method(*args, **kwargs)
        return res

    @staticmethod
    def get_token_from_header(request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth.startswith('Bearer '):
            return auth.split(' ')[1]
        return None

    @staticmethod
    def get_token_from_cookie(request, key: str) -> str:
        token = request.COOKIES.get(key, None)
        return token

    @staticmethod
    def get_token_from_request(request: Request | HttpRequest, key: str | MultiValueDict) -> str:
        token = None
        if isinstance(request, Request):
            token = request.data.get(key, None)
        elif isinstance(request, HttpRequest):
            token = request.POST.get(key, None)
            if not token:
                token = request.GET.get(key, None)
        return token

    def get_token(self, request, key: str = '') -> str:
        token = None
        if self.save_token_method == self.KeyCloakSaveTokenMethodChoices.COOKIE:
            token = self.get_token_from_cookie(request, key)
        elif self.save_token_method == self.KeyCloakSaveTokenMethodChoices.HEADER:
            if key == 'access_token':
                token = self.get_token_from_header(request)
            else:
                token = self.get_token_from_request(request, key)
        return token


class KeyCloakConfidentialClient(KeyCloakBaseManager):
    default_client_roles = [
        'offline_access',
        'uma_authorization',
        'default-roles-markaz',
    ]
    KEYCLOAK_TOKEN_CACHE_KEY = 'keycloak_credentials_client_access_token'
    KEYCLOAK_TOKEN_EXPIRE_KEY = 'keycloak_credentials_client_access_token_expiry'

    class KeyCloakRequestTypeChoices(TextChoices):
        CLIENT_CREDENTIALS_ACCESS_TOKEN = "CLIENT_CREDENTIALS_ACCESS_TOKEN", _("Client Credentials Access Token")
        PASSWORD_ACCESS_TOKEN = "PASSWORD_ACCESS_TOKEN", _("Password Access Token")
        REFRESH_ACCESS_TOKEN = "REFRESH_ACCESS_TOKEN", _("Refresh Access Token")
        INTROSPECT_TOKEN = "INTROSPECT_TOKEN", _("Introspect Token")
        USER_INFO = "USER_INFO", _("User Info")
        LOGOUT = "LOGOUT", _("Logout")
        JWKS_VERIFY = "JWKS_VERIFY", _("JWKS Verify")
        # TODO : add admin tokens
        GROUPS = "GROUPS", _("Groups")
        USERS = "USERS", _("Users")
        USER_ROLES = "USER_ROLES", _("User Roles")
        USER_GROUPS = "USER_GROUPS", _("User Groups")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.client_secret = get_settings_value('KEYCLOAK_CLIENT_SECRET')
        self.client_type = self.KeyCloakClientTypeChoices.CONFIDENTIAL

        # self.keycloak_openid = KeycloakOpenID(
        #     server_url=f"{self.base_prefix_url}/",
        #     realm_name=self.realm,
        #     client_id=self.client_id,
        #     client_secret_key=self.client_secret,
        # )

    def set_client_access_token(self, headers: dict) -> dict[str, str]:
        access_token = self.get_cached_access_token()
        headers.update({"Authorization": f"Bearer {access_token}"})
        return headers

    def _get_jwks(self):
        global _jwks
        if not _jwks:
            resp = requests.get(
                self.jwks_url,
                verify=False,
                # verify=get_settings_value('ENVIRONMENT') == 'prod',
            )
            resp.raise_for_status()
            _jwks = resp.json()
        return _jwks

    def decode_token(self, token: str):
        jwks = self._get_jwks()
        try:
            decoded_content = jwt.decode(
                token,
                jwks,
                algorithms=[self.algorithms],
                audience=self.user_audience,
                # issuer=self.issuer
            )
        except (jose_exceptions.JWTError, jose_exceptions.ExpiredSignatureError, jose_exceptions.JWTClaimsError) as e:
            raise self.KeyCloakException(f"Failed to decode token : {str(e)}")
        return decoded_content

    @staticmethod
    def set_httponly_cookie(key: str, value: str, response: Optional[Response] = None, *args, **kwargs) -> Response:
        if not response:
            response = Response(status=status.HTTP_200_OK)
        ssl_status = get_settings_value('SSL_STATUS')
        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=ssl_status,
            expires=timezone.now() + datetime.timedelta(hours=1),
            samesite='None' if ssl_status else "Lax",  # allow cross-site cookie
            # samesite='Lax',
            # domain="127.0.0.1"
            *args,
            **kwargs
        )
        return response

    def get_cached_access_token(self):
        access_token = cache.get(self.KEYCLOAK_TOKEN_CACHE_KEY)
        expiry_time = cache.get(self.KEYCLOAK_TOKEN_EXPIRE_KEY)
        if access_token and expiry_time and expiry_time > time.time():
            return access_token
        return self._post_client_credentials_access_token()

    def _post_client_credentials_access_token(self, *args, **kwargs):
        endpoint = "/protocol/openid-connect/token"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        post_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.POST,
            extra_headers=None,
            post_data=post_data,
            is_admin=False
        )
        if response_data:
            access_token = response_data.get('access_token')
            expires_in = response_data.get('expires_in', 300)  # seconds (default 5 mins)
            cache.set(
                self.KEYCLOAK_TOKEN_CACHE_KEY,
                access_token,
                timeout=expires_in - 30
            )
            cache.set(self.KEYCLOAK_TOKEN_EXPIRE_KEY, time.time() + expires_in - 30, timeout=expires_in - 30)
            return access_token

        raise self.KeyCloakException(_("Failed to retrieve data"))

    def _post_password_access_token(self, username: str, password: str, *args, **kwargs):
        endpoint = "/protocol/openid-connect/token"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        post_data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
        }
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.POST,
            extra_headers=None,
            post_data=post_data,
            is_admin=False
        )

        if response_data:
            return response_data.get('access_token', None)
        else:
            raise self.KeyCloakException(_("Failed to retrieve data"))

    def _post_refresh_access_token(self, refresh_token: str, client_id: str = None, *args, **kwargs) -> dict:
        endpoint = "/protocol/openid-connect/token"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        post_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        if client_id:
            post_data.update({
                "client_id": client_id,
            })
        else:
            post_data.update({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.POST,
            extra_headers=None,
            post_data=post_data,
            is_admin=False
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve data"))
        return response_data

    def _post_logout(self, refresh_token: str, client_id: str = None, *args, **kwargs) -> dict:
        endpoint = "/protocol/openid-connect/logout"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        post_data = {
            "refresh_token": refresh_token
        }
        if client_id:
            post_data.update({
                "client_id": client_id,
            })
        else:
            post_data.update({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.POST,
            extra_headers=None,
            post_data=post_data,
            is_admin=False
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve data"))
        return response_data

    def _get_groups(self, *args, **kwargs) -> dict:
        """
        Retrieves all groups from Keycloak using the Admin REST API.
        Requires a valid admin-level access token.
        """
        endpoint = "/groups"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        extra_headers = {
            "Content-Type": "application/json"
        }
        extra_headers = self.set_client_access_token(extra_headers)
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.GET,
            extra_headers=extra_headers,
            post_data=None,
            is_admin=True
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve groups from Keycloak"))

        return response_data

    def _get_users(self, *args, **kwargs) -> dict:
        """
        Retrieves all users from Keycloak using the Admin REST API.
        Requires a valid admin-level access token.
        """
        endpoint = "/users"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        extra_headers = {
            "Content-Type": "application/json"
        }
        extra_headers = self.set_client_access_token(extra_headers)
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.GET,
            extra_headers=extra_headers,
            post_data=None,
            is_admin=True
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve users from Keycloak"))

        return response_data

    def _get_user_roles(self, detail_pk: str, *args, **kwargs) -> dict:
        """
        Retrieves all users from Keycloak using the Admin REST API.
        Requires a valid admin-level access token.
        """
        # endpoint = "/users/{userId}/role-mappings/realm"
        # endpoint = "/users/{userId}/role-mappings/clients/{clientUUID}"
        endpoint = f"/users/{detail_pk}/role-mappings"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        extra_headers = {
            "Content-Type": "application/json"
        }
        extra_headers = self.set_client_access_token(extra_headers)
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.GET,
            extra_headers=extra_headers,
            post_data=None,
            is_admin=True
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve user roles from Keycloak"))

        return response_data

    def _get_user_groups(self, detail_pk: str, *args, **kwargs) -> dict:
        """
        Retrieves all users from Keycloak using the Admin REST API.
        Requires a valid admin-level access token.
        """
        # endpoint = "/users/{userId}/role-mappings/realm"
        # endpoint = "/users/{userId}/role-mappings/clients/{clientUUID}"
        endpoint = f"/users/{detail_pk}/groups"
        endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        extra_headers = {
            "Content-Type": "application/json"
        }
        extra_headers = self.set_client_access_token(extra_headers)
        response_data = self._get_request_data(
            endpoint=endpoint,
            request_method=self.KeyCloakRequestMethodChoices.GET,
            extra_headers=extra_headers,
            post_data=None,
            is_admin=True
        )

        if not response_data:
            raise self.KeyCloakException(_("Failed to retrieve user roles from Keycloak"))

        return response_data
    # def decode_token_v2(self, token):
    #     try:
    #         return self.keycloak_openid.decode_token(
    #             token,
    #             key=self.keycloak_openid.public_key(),
    #             options={"verify_signature": True, "verify_aud": False}
    #         )
    #     except Exception:
    #         raise JWTError('Invalid token')
    # raise AuthenticationFailed('Invalid token')


class KeyCloakPublicClient(KeyCloakBaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_type = self.KeyCloakClientTypeChoices.PUBLIC
