import logging
from datetime import timedelta
from typing import Type, Optional
from urllib.parse import urlencode

import requests
from django.db.models import TextChoices, Model, QuerySet
from django.utils.translation import gettext_lazy as _
from requests.exceptions import HTTPError

from django_keycloak_sso.api.serializers import GroupSerializer, UserSerializer
from django_keycloak_sso.caching import SSOCacheControlKlass
from django_keycloak_sso.helpers import get_settings_value
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from django_keycloak_sso.sso.authentication import CustomUser, CustomGroup

logger = logging.getLogger(__name__)


class SSOKlass:
    class SSOKlassException(Exception):
        pass

    class SSOKlassNotFoundException(Exception):
        pass

    class CompanyGroupRoleChoices(TextChoices):
        MANAGER = "MANAGER", _("Manager")
        ASSISTANT = "ASSISTANT", _("Assistant")
        EMPLOYEE = "EMPLOYEE", _("Employee")

    class SSODataTypeChoices(TextChoices):
        USER = "USER", _("User")
        USER_ROLE = "USER_ROLE", _("User Role")
        COMPANY_GROUP = "COMPANY_GROUP", _("Company Group")

    class SSODataFormChoices(TextChoices):
        DETAIL = "DETAIL", _("Detail")
        LIST = "LIST", _("List")
        CUSTOM = "CUSTOM", _("Custom")

    class SSOFieldTypeChoices(TextChoices):
        GROUP = "GROUP", "GROUP"
        USER = "USER", "USER"
        ROLE = "ROLE", "ROLE"

    sso_request_exceptions = (
        SSOKlassException,
        SSOKlassNotFoundException,
        KeyCloakConfidentialClient.KeyCloakException,
        KeyCloakConfidentialClient.KeyCloakNotFoundException
    )

    def __init__(self):
        self.sso_url = get_settings_value('SSO_SERVICE_BASE_URL')
        self.sso_admin_url = f"{self.sso_url}/admin-panel/v1"
        self.keycloak_klass = KeyCloakConfidentialClient()
        self.sso_cache_klass = SSOCacheControlKlass()

    @classmethod
    def validate_enums_value(cls, value: str, enums_class: Type[TextChoices]):
        if value not in enums_class.values:
            raise cls.SSOKlassException(
                "Value is not exists in that enums"
            )

    @staticmethod
    def _build_filter_url(*, base_url: str, ids_filtering_list: list = None, id_range_filtering_list: list = None):
        # Define query parameters dictionary
        query_params = {}
        #
        # # Handle `ids_filtering_list`
        # if ids_filtering_list:
        #     query_params['ids'] = ','.join(map(str, ids_filtering_list))
        #
        # # Handle `id_range_filtering_list`
        # if id_range_filtering_list:
        #     if len(id_range_filtering_list) == 2:
        #         query_params['id_range'] = f"{id_range_filtering_list[0]},{id_range_filtering_list[1]}"
        #     else:
        #         raise ValueError("id_range_filtering_list must contain exactly two elements (start_id, end_id)")

        # Append query parameters to base URL
        return f"{base_url}?{urlencode(query_params)}" if query_params else base_url

    def _get_headers(self):
        """Helper method to generate headers for the request."""
        return {
            # 'Authorization': f"{self.client_authorization_method} {self.client_token}",
            'Content-Type': 'application/json',
            # 'client-key': self.client_key,
            # 'client-token': self.client_token,
        }

    def _get_request_data(self, endpoint, is_admin_panel=False):
        """Internal method to send GET requests to the SSO server."""
        if is_admin_panel:
            url = f"{self.sso_admin_url}/{endpoint}"
        else:
            url = f"{self.sso_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        # TODO : fix this dumb handler
        except HTTPError as http_err:
            if http_err.response.status_code == 404:
                # return None
                raise self.SSOKlassNotFoundException("Url or object was not found : 404 error")
            logger.error(http_err)
            # return None
            raise self.SSOKlassException(http_err)
        except Exception as err:
            logger.error(err)
            # return None
            raise self.SSOKlassException(err)

    def get_sso_data(self, data_type: SSODataTypeChoices, data_form: SSODataFormChoices, *args, **kwargs):
        self.validate_enums_value(data_type, self.SSODataTypeChoices)
        self.validate_enums_value(data_form, self.SSODataFormChoices)
        if data_form == self.SSODataFormChoices.DETAIL:
            obj_pk = kwargs.get('pk', None)
            if not obj_pk:
                raise self.SSOKlassException(_("Get detail of a object need object pk"))
        # if data_form == self.SSODataFormChoices.LIST:
        #     ids_filtering_list = kwargs.get('ids_filtering_list', list())
        #     if not ids_filtering_list:
        #         return []
        #     kwargs['ids_filtering_list'] = [value for value in ids_filtering_list if value is not None]
        get_data_method = getattr(self, f'get_{data_type.lower()}_{data_form.lower()}_data')
        if not get_data_method or not callable(get_data_method):
            raise self.SSOKlassException("Data get method for sso data is not valid")
        # try:
        res = get_data_method(*args, **kwargs)
        # except self.SSOKlassException:
        #     res = None
        if data_form == self.SSODataFormChoices.LIST:
            if res:
                return res
                # res = res['results'] if 'results' in res else []
            else:
                res = []
        return res

    def check_object_exists(self, data_type: SSODataTypeChoices, obj_id: int) -> bool:
        try:
            res = self.get_sso_data(data_type, self.SSODataFormChoices.DETAIL, pk=obj_id)
            return True
        except self.sso_request_exceptions as e:
            return False

    def get_user_detail_data(self, pk, *args, **kwargs):
        """Public method to get user data from SSO based on user ID."""
        # endpoint = f"accounts/users/{pk}"
        # user_data = self._get_request_data(endpoint, is_admin_panel=True)
        user_data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.USERS,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
            detail_pk=pk,
        )
        if user_data:
            return user_data
        else:
            raise self.SSOKlassException(_("Failed to retrieve data with user ID"))

    def get_user_list_data(self, *args, **kwargs):
        """Public method to search users on the SSO server."""
        # endpoint = "accounts/users/"
        # users_data = self._get_request_data(endpoint, is_admin_panel=True)
        users_data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.USERS,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
        )
        if users_data:
            return users_data
        raise self.SSOKlassException(_("Failed to retrieve user list data"))

    def get_user_role_list_data(self, *args, **kwargs):
        """Public method to search users on the SSO server."""
        # endpoint = "accounts/roles/"
        # users_data = self._get_request_data(endpoint, is_admin_panel=True)
        users_data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.USER_ROLES,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
            detail_pk='1234',
        )
        if users_data:
            return users_data
        raise self.SSOKlassException(_("Failed to retrieve user role list data"))

    # TODO : write all these methods with keycloak
    def get_company_group_list_data(self, *args, **kwargs):
        """Public method to search users on the SSO server."""
        # endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
        # data = self._get_request_data(endpoint, is_admin_panel=True)
        data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.GROUPS,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
        )
        if data:
            return data
        raise self.SSOKlassException(_("Failed to retrieve company groups list data"))

    def get_company_group_detail_data(self, pk, *args, **kwargs):
        """Public method to search users on the SSO server."""
        # endpoint = f"accounts/groups/{pk}/"
        # data = self._get_request_data(endpoint, is_admin_panel=True)
        data = self.keycloak_klass.send_request(
            self.keycloak_klass.KeyCloakRequestTypeChoices.GROUPS,
            self.keycloak_klass.KeyCloakRequestTypeChoices,
            self.keycloak_klass.KeyCloakRequestMethodChoices.GET,
            self.keycloak_klass.KeyCloakPanelTypeChoices.ADMIN,
            detail_pk=pk

        )
        if data:
            return data
        raise self.SSOKlassException(_("Failed to retrieve company groups detail data"))

    # TODO : modify this for works with keycloak
    @staticmethod
    def has_user_role_in_group(user_groups: list[dict], group_id: int, user_role: CompanyGroupRoleChoices):
        """
        Check if the user is a manager in the given group.

        Args:
            user_groups (list): List of groups the user has joined.
            group_id (int): The ID of the group to check.
            user_role (str): Role to check.

        Returns:
            bool: True if the user has role in the specified group, otherwise False.
        """
        for group_data in user_groups:
            if group_data['group']['id'] == group_id and group_data['role'] == user_role:
                return True
        return False

    # TODO : modify this for works with keycloak
    @classmethod
    def get_obj_by_id(cls, data_list, obj_id):
        for data_ in data_list:
            if data_.get('id') == obj_id:
                return data_
        raise cls.SSOKlassNotFoundException(f"Group with ID {obj_id} not found.")

    def get_sso_data_list(self, queryset: QuerySet | list, field_name: str, field_type: SSOFieldTypeChoices) -> list:
        list_data = self.sso_cache_klass.get_cached_value(field_type=field_type)
        if not list_data:
            list_data = list()
            if queryset and (isinstance(queryset, QuerySet) or isinstance(queryset, list)):
                # list_ids = queryset.values_list(field_name, flat=True)
                list_ids = []
                if field_type == self.SSOFieldTypeChoices.GROUP:
                    data_type = SSOKlass.SSODataTypeChoices.COMPANY_GROUP
                elif field_type == self.SSOFieldTypeChoices.USER:
                    data_type = SSOKlass.SSODataTypeChoices.USER
                else:
                    raise ValueError("field_type is not valid")
                list_data = self.get_sso_data(
                    data_type=data_type,
                    data_form=SSOKlass.SSODataFormChoices.LIST,
                    ids_filtering_list=list_ids,
                )
                self.sso_cache_klass.set_cache_value(
                    field_type=field_type,
                    value=list_data,
                    timeout=timedelta(hours=1).seconds
                )

        return list_data

    def get_serializer_field_data(
            self,
            field_name: str,
            field_type: SSOFieldTypeChoices,
            obj_: Model,
            list_data: Optional[list] = None,
            get_from_list: bool = False
    ) -> dict | None:
        has_error = False
        data = None
        if get_from_list:
            try:
                data = self.get_obj_by_id(list_data, getattr(obj_, field_name))
            except SSOKlass.SSOKlassNotFoundException as e:
                has_error = True
        if not get_from_list or (get_from_list and has_error):
            try:
                data = getattr(obj_, f"{field_name}_data", None)
                if data:
                    data = data.payload
                else:
                    if field_type == self.SSOFieldTypeChoices.GROUP:
                        data = self.get_company_group_detail_data(getattr(obj_, field_name))
                    elif field_type == self.SSOFieldTypeChoices.USER:
                        data = self.get_user_detail_data(getattr(obj_, field_name))
                    else:
                        raise ValueError("field_type is not valid")
            except self.sso_request_exceptions as e:
                print(e)
        if not data:
            return None
        if field_type == self.SSOFieldTypeChoices.GROUP:
            data = GroupSerializer(CustomGroup(payload=data)).data
        elif field_type == self.SSOFieldTypeChoices.USER:
            data = UserSerializer(CustomUser(payload=data, is_authenticated=False)).data
        return data
