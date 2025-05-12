# from typing import Type
# from urllib.parse import urlencode
#
# import requests
# from django.db.models import TextChoices
# from django.utils.translation import gettext_lazy as _
# from requests.exceptions import HTTPError
#
# from core.libs.logging import LogInfo
# from core.libs.sso.helpers import get_settings_value
#
#
# class SSOKlass:
#     class SSOKlassException(Exception):
#         pass
#
#     class SSOKlassNotFoundException(Exception):
#         pass
#
#     class CompanyGroupRoleChoices(TextChoices):
#         MANAGER = "MANAGER", _("Manager")
#         ASSISTANT = "ASSISTANT", _("Assistant")
#         EMPLOYEE = "EMPLOYEE", _("Employee")
#
#     class SSODataTypeChoices(TextChoices):
#         USER = "USER", _("User")
#         USER_ROLE = "USER_ROLE", _("User Role")
#         COMPANY_GROUP = "COMPANY_GROUP", _("Company Group")
#
#     class SSODataFormChoices(TextChoices):
#         DETAIL = "DETAIL", _("Detail")
#         LIST = "LIST", _("List")
#         CUSTOM = "CUSTOM", _("Custom")
#
#     def __init__(self):
#         self.client_authorization_method = get_settings_value('SSO_SERVICE_AUTHORIZATION_METHOD')
#         self.client_key = get_settings_value('SSO_SERVICE_AUTHORIZATION_KEY')
#         self.client_token = get_settings_value('SSO_SERVICE_AUTHORIZATION_TOKEN')
#         self.sso_url = get_settings_value('SSO_SERVICE_BASE_URL')
#         self.sso_admin_url = f"{self.sso_url}/admin-panel/v1"
#
#     @classmethod
#     def validate_enums_value(cls, value: str, enums_class: Type[TextChoices]):
#         if value not in enums_class.values:
#             raise cls.SSOKlassException(
#                 "Value is not exists in that enums"
#             )
#
#     @staticmethod
#     def _build_filter_url(*, base_url: str, ids_filtering_list: list = None, id_range_filtering_list: list = None):
#         # Define query parameters dictionary
#         query_params = {}
#
#         # Handle `ids_filtering_list`
#         if ids_filtering_list:
#             query_params['ids'] = ','.join(map(str, ids_filtering_list))
#
#         # Handle `id_range_filtering_list`
#         if id_range_filtering_list:
#             if len(id_range_filtering_list) == 2:
#                 query_params['id_range'] = f"{id_range_filtering_list[0]},{id_range_filtering_list[1]}"
#             else:
#                 raise ValueError("id_range_filtering_list must contain exactly two elements (start_id, end_id)")
#
#         # Append query parameters to base URL
#         return f"{base_url}?{urlencode(query_params)}" if query_params else base_url
#
#     def _get_headers(self):
#         """Helper method to generate headers for the request."""
#         return {
#             # 'Authorization': f"{self.client_authorization_method} {self.client_token}",
#             'Content-Type': 'application/json',
#             'client-key': self.client_key,
#             'client-token': self.client_token,
#         }
#
#     def _get_request_data(self, endpoint, is_admin_panel=False):
#         """Internal method to send GET requests to the SSO server."""
#         if is_admin_panel:
#             url = f"{self.sso_admin_url}/{endpoint}"
#         else:
#             url = f"{self.sso_url}/{endpoint}"
#         try:
#             response = requests.get(url, headers=self._get_headers())
#             response.raise_for_status()
#             return response.json()
#         # TODO : fix this dumb handler
#         except HTTPError as http_err:
#             if http_err.response.status_code == 404:
#                 # return None
#                 raise self.SSOKlassNotFoundException("Url or object was not found : 404 error")
#             LogInfo.error(http_err, __name__)
#             # return None
#             raise self.SSOKlassException(http_err)
#         except Exception as err:
#             LogInfo.error(err, __name__)
#             # return None
#             raise self.SSOKlassException(err)
#
#     def get_sso_data(self, data_type: SSODataTypeChoices, data_form: SSODataFormChoices, *args, **kwargs):
#         self.validate_enums_value(data_type, self.SSODataTypeChoices)
#         self.validate_enums_value(data_form, self.SSODataFormChoices)
#         if data_form == self.SSODataFormChoices.DETAIL:
#             obj_pk = kwargs.get('pk', None)
#             if not obj_pk:
#                 raise self.SSOKlassException(_("Get detail of a object need object pk"))
#         if data_form == self.SSODataFormChoices.LIST:
#             ids_filtering_list = kwargs.get('ids_filtering_list', list())
#             if not ids_filtering_list:
#                 return []
#             kwargs['ids_filtering_list'] =  [value for value in ids_filtering_list if value is not None]
#         get_data_method = getattr(self, f'get_{data_type.lower()}_{data_form.lower()}_data')
#         if not get_data_method or not callable(get_data_method):
#             raise self.SSOKlassException("Data get method for sso data is not valid")
#         # try:
#         res = get_data_method(*args, **kwargs)
#         # except self.SSOKlassException:
#         #     res = None
#         if data_form == self.SSODataFormChoices.LIST:
#             if res:
#                 res = res['results'] if 'results' in res else []
#             else:
#                 res = []
#         return res
#
#     def check_object_exists(self, data_type: SSODataTypeChoices, obj_id: int) -> bool:
#         try:
#             res = self.get_sso_data(data_type, self.SSODataFormChoices.DETAIL, pk=obj_id)
#             return True
#         except (self.SSOKlassNotFoundException, self.SSOKlassException) as e:
#             return False
#
#     def get_user_detail_data(self, pk, *args, **kwargs):
#         """Public method to get user data from SSO based on user ID."""
#         endpoint = f"accounts/users/{pk}"
#         user_data = self._get_request_data(endpoint, is_admin_panel=True)
#
#         if user_data:
#             return user_data
#         else:
#             raise self.SSOKlassException(_("Failed to retrieve data with user ID"))
#
#     def get_user_list_data(self, *args, **kwargs):
#         """Public method to search users on the SSO server."""
#         endpoint = "accounts/users/"
#         users_data = self._get_request_data(endpoint, is_admin_panel=True)
#
#         if users_data:
#             return users_data
#         raise self.SSOKlassException(_("Failed to retrieve user list data"))
#
#     def get_user_role_list_data(self, *args, **kwargs):
#         """Public method to search users on the SSO server."""
#         endpoint = "accounts/roles/"
#         users_data = self._get_request_data(endpoint, is_admin_panel=True)
#
#         if users_data:
#             return users_data
#         raise self.SSOKlassException(_("Failed to retrieve user role list data"))
#
#     def get_company_group_list_data(self, *args, **kwargs):
#         """Public method to search users on the SSO server."""
#         endpoint = "accounts/groups/"
#         endpoint = self._build_filter_url(base_url=endpoint, **kwargs)
#         data = self._get_request_data(endpoint, is_admin_panel=True)
#
#         if data:
#             return data
#         raise self.SSOKlassException(_("Failed to retrieve company groups list data"))
#
#     def get_company_group_detail_data(self, pk, *args, **kwargs):
#         """Public method to search users on the SSO server."""
#         endpoint = f"accounts/groups/{pk}/"
#         data = self._get_request_data(endpoint, is_admin_panel=True)
#
#         if data:
#             return data
#         raise self.SSOKlassException(_("Failed to retrieve company groups detail data"))
#
#     @staticmethod
#     def has_user_role_in_group(user_groups: list[dict], group_id: int, user_role: CompanyGroupRoleChoices):
#         """
#         Check if the user is a manager in the given group.
#
#         Args:
#             user_groups (list): List of groups the user has joined.
#             group_id (int): The ID of the group to check.
#             user_role (str): Role to check.
#
#         Returns:
#             bool: True if the user has role in the specified group, otherwise False.
#         """
#         for group_data in user_groups:
#             if group_data['group']['id'] == group_id and group_data['role'] == user_role:
#                 return True
#         return False
#
#     @classmethod
#     def get_obj_by_id(cls, data_list, obj_id):
#         for data_ in data_list:
#             if data_.get('id') == obj_id:
#                 return data_
#         raise cls.SSOKlassNotFoundException(f"Group with ID {obj_id} not found.")
