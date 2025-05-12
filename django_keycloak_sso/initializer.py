from .helpers import get_settings_value


class KeyCloakInitializer:
    realm = get_settings_value('KEYCLOAK_REALM')
    client_id = get_settings_value('KEYCLOAK_CLIENT_ID')
    client_title = get_settings_value('KEYCLOAK_CLIENT_TITLE')
    client_name = get_settings_value('KEYCLOAK_CLIENT_NAME')
    algorithms = get_settings_value('KEYCLOAK_ALGORITHMS')
    user_audience = "account"
    base_prefix_url = get_settings_value('KEYCLOAK_SERVER_URL')
    base_panel_url = f'{base_prefix_url}/realms/{realm}'
    base_admin_url = f'{base_prefix_url}/admin/realms/{realm}'
    jwks_url = f"{base_panel_url}/protocol/openid-connect/certs"
    issuer_prefix = get_settings_value('KEYCLOAK_ISSUER_PREFIX')
    issuer = f'{issuer_prefix}/realms/{realm}'
    client_secret = get_settings_value('KEYCLOAK_CLIENT_SECRET')
