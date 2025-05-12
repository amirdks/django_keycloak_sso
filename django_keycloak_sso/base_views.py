from rest_framework.views import APIView

from .package_helpers import get_package_settings

class BaseKeycloakAdminView(APIView):
    def get_permissions(self):
        # TODO : create a documentation for permission_classes_override utility
        permission_classes = getattr(self, 'permission_classes_override', None)
        if permission_classes is not None:
            return [p() for p in permission_classes]
        return [p() for p in get_package_settings(
            'KEYCLOAK_DEFAULT_ADMIN_PANEL_PERMISSION_CLASSES',
            'list',
            True
        )]
