from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from django_keycloak_sso.sso.utils import check_user_permission_access


def check_permission_decorator(
        role_titles=None, group_titles=None, group_roles=None, match_group_roles=False
):
    role_titles = role_titles or []
    group_titles = group_titles or []
    group_roles = group_roles or []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                raise PermissionDenied(_("Authentication required"))

            # Run the access check
            has_access = check_user_permission_access(
                user=user,
                role_titles=role_titles,
                group_titles=group_titles,
                group_roles=group_roles,
                match_group_roles=match_group_roles
            )

            if not has_access:
                raise PermissionDenied(_("You are not allowed to access this API"))

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def require_roles(*role_titles):
    return check_permission_decorator(role_titles=list(role_titles))


def require_groups(*group_titles):
    return check_permission_decorator(group_titles=list(group_titles))


def require_group_roles(*group_roles):
    return check_permission_decorator(group_roles=list(group_roles))


def require_all_permissions(*, role_titles=None, group_titles=None, group_roles=None):
    return check_permission_decorator(
        role_titles=role_titles or [],
        group_titles=group_titles or [],
        group_roles=group_roles or []
    )
