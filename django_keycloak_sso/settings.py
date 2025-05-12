from .helpers import get_settings_value

# TODO: modfy this import for package
KEYCLOAK_DEFAULT_ADMIN_PANEL_PERMISSION_CLASSES = get_settings_value(
    "KEYCLOAK_DEFAULT_ADMIN_PANEL_PERMISSION_CLASSES",
    ("account_module.permissions.IsSuperUserOrManagerAccess",)
)
