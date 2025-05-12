from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from django_keycloak_sso.keycloak import KeyCloakConfidentialClient
from django_keycloak_sso.sso.utils import check_user_permission_access


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


class IsAdminAccess(IsAuthenticated):
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
