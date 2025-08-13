from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from django_keycloak_sso.sso.utils import check_user_permission_access
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from django_keycloak_sso.initializer import KeyCloakInitializer


class IsManagerAccess(IsAuthenticated):
    def has_permission(self, request, view):
        role_titles = []
        group_titles = []
        group_roles = [KeyCloakConfidentialClient.KeyCloakGroupRoleChoices.MANAGER]
        is_authenticated = super().has_permission(request, view)
        access_status = is_authenticated and check_user_permission_access(
            request.user, role_titles, group_titles, group_roles, False
        )
        if not access_status:
            raise PermissionDenied(_("You are not allowed to access this api"))
        return True


class IsSuperUserAccess(IsAuthenticated):
    def has_permission(self, request, view):
        role_titles = ['superuser']
        group_titles = []
        group_roles = []
        is_authenticated = super().has_permission(request, view)
        access_status = is_authenticated and check_user_permission_access(
            request.user, role_titles, group_titles, group_roles, False
        )
        if not access_status:
            raise PermissionDenied(_("You are not allowed to access this api"))
        return True


class IsSuperUserOrManagerAccess(IsAuthenticated):
    def has_permission(self, request, view):
        role_titles = ['superuser']
        group_titles = []
        group_roles = []
        is_authenticated = super().has_permission(request, view)
        access_status = is_authenticated and check_user_permission_access(
            request.user, role_titles, group_titles, group_roles, False
        )
        if access_status:
            return True
        group_roles.append(KeyCloakConfidentialClient.KeyCloakGroupRoleChoices.MANAGER)
        access_status = is_authenticated and check_user_permission_access(
            request.user, role_titles, group_titles, group_roles, False
        )
        if access_status:
            return True
        raise PermissionDenied(_("You are not allowed to access this api"))

class IsAuthenticatedAccess(IsAuthenticated):
    """
    Default permission class for authenticated users integrated with Keycloak.
    Only allows access if user is authenticated and validated by check_user_permission_access.
    """
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)

        access_status = is_authenticated and check_user_permission_access(
            request.user,
            role_titles=[],
            group_titles=[],
            group_roles=[],
            raise_exception=False
        )

        if not access_status:
            raise PermissionDenied(_("You are not allowed to access this API"))

        return True

class GroupAccess(KeyCloakInitializer):
    """
    You can check if a user has the allowed group by sending the name of the desired group and
    request.user and setting the admin group in .env.
    """

    def require_all_groups(self, user , groups_name: list):

        groups_list = user.groups
        if not any(admin in groups_list for admin in self.admin_groups) and not all(item in groups_list for item in groups_name):
            raise PermissionDenied('You are not allowed to access this API')
        return True

    def require_any_groups(self, user, groups_names: list):
        groups_list = user.groups

        if not (
                any(admin in groups_list for admin in self.admin_groups)
                or any(item in groups_list for item in groups_names)
        ):
            raise PermissionDenied('You are not allowed to access this API')
        return True

