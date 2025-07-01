from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from django_keycloak_sso.sso.utils import check_user_permission_access
from django_keycloak_sso.keycloak import KeyCloakConfidentialClient


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
