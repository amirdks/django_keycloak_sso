import jwt
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from . import helpers
from .helpers import CustomGetterObjectKlass


class CustomGroup(CustomGetterObjectKlass):
    def __repr__(self):
        return f"<CustomGroup(id={self.id if bool(self) else 'None'})>"

    @property
    def get_user_ids(self):
        """
        Extract a list of unique user IDs from the given data.
        """
        user_ids = set()
        for user_group in self.user_groups:
            user = user_group.get('user')
            if user and 'id' in user:
                user_ids.add(user['id'])
        return list(user_ids)

    @property
    def payload(self) -> dict:
        return self._payload


class CustomUser(CustomGetterObjectKlass):
    client_title = KeyCloakConfidentialClient.client_title

    def __init__(self, is_authenticated: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_authenticated = is_authenticated

    def __repr__(self):
        return f"<CustomUser(id={self.id if bool(self) else 'None'}, is_authenticated={self.is_authenticated})>"

    # @property
    # def primary_group(self):
    #     for entry in self.groups:
    #         if entry.get('is_main_group'):
    #             return CustomGroup(entry['group'])
    #     return None

    @property
    def groups(self):
        groups_list = []
        if 'groups' not in self.payload:
            return groups_list
        for entry in self.payload['groups']:
            groups_list.append(entry)
        return groups_list

    @property
    def groups_dict_list(self):
        group_list = []
        if 'groups' not in self.payload:
            return group_list
        for path in self.groups:
            parts = path.strip("/").split("/")
            if len(parts) == 2:
                group_name, role_name = parts
                role_name = role_name[:-1] if role_name.endswith('s') else role_name
                group_list.append({
                    'title': group_name,
                    'role': role_name,
                })
        return group_list

    @property
    def groups_parent(self) -> list[str]:
        group_names = []
        if 'groups' not in self.payload:
            return group_names
        for path in self.groups:
            parts = path.strip("/").split("/")
            if len(parts) == 2:
                group_name, _ = parts
                group_names.append(group_name)
        return group_names

    @property
    def group_roles(self) -> list[str]:
        group_roles = []
        if 'groups' not in self.payload:
            return group_roles
        for path in self.groups:
            parts = path.strip("/").split("/")
            if len(parts) == 2:
                _, role_name = parts
                role_name = role_name[:-1] if role_name.endswith('s') else role_name
                group_roles.append(role_name)
        return group_roles

    @property
    def realm_roles(self):
        realm_roles = []
        if 'realm_access' not in self.payload:
            return realm_roles
        if 'roles' not in self.realm_access:
            return realm_roles
        for entry in self.realm_access['roles']:
            if entry in KeyCloakConfidentialClient.default_client_roles or entry.startswith(
                    f'{settings.KEYCLOAK_CLIENT_NAME}.'):
                continue
            realm_roles.append(entry)
        return realm_roles

    @property
    def client_roles(self):
        client_roles = []
        if 'resource_access' not in self.payload:
            return client_roles
        for entry in self.resource_access.get(self.client_title, {}).get('roles', []):
            client_roles.append(entry)
        return client_roles

    @property
    def roles(self):
        roles = []
        roles += self.realm_roles
        roles += self.client_roles
        return roles

    @property
    def id(self):
        return self.sub

    @property
    def username(self):
        if 'username' in self.payload:
            return self.payload['username']
        elif 'preferred_username' in self.payload:
            return self.preferred_username
        return str(self.id)

    @property
    def first_name(self):
        if 'first_name' in self.payload:
            return self.payload['first_name']
        elif 'firstName' in self.payload:
            return self.firstName
        elif 'given_name' in self.payload:
            return self.given_name
        return ""

    @property
    def last_name(self):
        if 'last_name' in self.payload:
            return self.payload['last_name']
        elif 'lastName' in self.payload:
            return self.lastName
        elif 'family_name' in self.payload:
            return self.family_name
        return ""

    @property
    def full_name(self):
        if 'full_name' in self.payload:
            return self.payload['full_name']
        elif 'name' in self.payload:
            return self.name
        else:
            first_name = self.first_name
            last_name = self.last_name
            if first_name and last_name:
                return f"{first_name} {last_name}"
        return ""

    @property
    def payload(self) -> dict:
        return self._payload

    @property
    def groups_id(self):
        cached_data = self._get_cached_value('groups_id')

        if cached_data is not None:
            return cached_data

        user_group_data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.USER_GROUPS,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
            detail_pk=self.id,
        )
        groups_id_list = []
        for entry in user_group_data:
            # groups_id_list.append(entry['group']['id'])
            groups_id_list.append(entry['parentId'])
        self._set_cache_value('groups_id', groups_id_list, 3600)
        return groups_id_list


class CustomJWTAuthentication(BaseAuthentication):
    """
    Custom authentication class that validates a JWT token from the request.
    If valid, stores payload in request.user_data; if invalid or expired, raises 403.
    """

    def __init__(self):
        super().__init__()
        self.jwt_signing_key = helpers.get_settings_value('SIGNING_KEY')
        self.jwt_algorithm = helpers.get_jwt_algorithm()

    def authenticate(self, request: Request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            raise AuthenticationFailed(_("Invalid token format."))
        try:
            payload = jwt.decode(
                token,
                self.jwt_signing_key,
                algorithms=[self.jwt_algorithm],
                verify=True,
                options={"verify_signature": True}
            )
            user = CustomUser(payload=payload, is_authenticated=True)
            return user, token
        except ExpiredSignatureError:
            raise AuthenticationFailed("JWT token has expired.")
        except InvalidTokenError:
            raise AuthenticationFailed("Invalid JWT token.")
