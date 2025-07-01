# django_keycloak_sso/documentation.py
"""
Universal API documentation system compatible with both drf-spectacular and drf-yasg
"""
import logging
from typing import Any, Dict, Optional, Union, List

logger = logging.getLogger(__name__)

# Try to import both libraries
try:
    from drf_spectacular.utils import extend_schema

    HAS_SPECTACULAR = True
except ImportError:
    HAS_SPECTACULAR = False
    extend_schema = None

try:
    from drf_yasg.utils import swagger_auto_schema

    HAS_YASG = True
except ImportError:
    HAS_YASG = False
    swagger_auto_schema = None


class APIDocumentation:
    """
    Universal API documentation decorator that works with both drf-spectacular and drf-yasg
    """

    @staticmethod
    def auto_schema(
            # Common parameters
            operation_summary: Optional[str] = None,
            operation_description: Optional[str] = None,
            tags: Optional[List[str]] = None,
            request_body: Optional[Any] = None,
            responses: Optional[Dict[Union[int, str], Any]] = None,

            # drf-spectacular specific
            parameters: Optional[List[Any]] = None,
            examples: Optional[List[Any]] = None,
            deprecated: Optional[bool] = None,
            filters: Optional[bool] = None,

            # drf-yasg specific
            manual_parameters: Optional[List[Any]] = None,
            operation_id: Optional[str] = None,

            # Fallback behavior
            prefer_spectacular: bool = True,
    ):
        """
        Universal decorator for API documentation

        Args:
            operation_summary: Brief summary of the operation
            operation_description: Detailed description of the operation
            tags: List of tags for grouping operations
            request_body: Request body serializer or schema
            responses: Dictionary of response codes and their schemas
            parameters: List of parameters (drf-spectacular)
            examples: List of examples (drf-spectacular)
            deprecated: Whether the endpoint is deprecated
            filters: Whether to include filter parameters
            manual_parameters: Manual parameters (drf-yasg)
            operation_id: Operation ID (drf-yasg)
            prefer_spectacular: Whether to prefer spectacular when both are available
        """

        def decorator(func):
            # If both are available, use the preferred one
            if HAS_SPECTACULAR and HAS_YASG:
                if prefer_spectacular:
                    return APIDocumentation._apply_spectacular(
                        func, operation_summary, operation_description, tags,
                        request_body, responses, parameters, examples, deprecated, filters
                    )
                else:
                    return APIDocumentation._apply_yasg(
                        func, operation_summary, operation_description, tags,
                        request_body, responses, manual_parameters, operation_id
                    )

            # Use spectacular if available
            elif HAS_SPECTACULAR:
                return APIDocumentation._apply_spectacular(
                    func, operation_summary, operation_description, tags,
                    request_body, responses, parameters, examples, deprecated, filters
                )

            # Use yasg if available
            elif HAS_YASG:
                return APIDocumentation._apply_yasg(
                    func, operation_summary, operation_description, tags,
                    request_body, responses, manual_parameters, operation_id
                )

            # No documentation library available
            else:
                logger.warning(
                    "Neither drf-spectacular nor drf-yasg is installed. "
                    "API documentation will not be generated."
                )
                return func

        return decorator

    @staticmethod
    def _apply_spectacular(func, summary, description, tags, request_body,
                           responses, parameters, examples, deprecated, filters):
        """Apply drf-spectacular documentation"""
        kwargs = {}

        if summary:
            kwargs['summary'] = summary
        if description:
            kwargs['description'] = description
        if tags:
            kwargs['tags'] = tags
        if request_body:
            kwargs['request'] = request_body
        if responses:
            kwargs['responses'] = responses
        if parameters:
            kwargs['parameters'] = parameters
        if examples:
            kwargs['examples'] = examples
        if deprecated is not None:
            kwargs['deprecated'] = deprecated
        if filters is not None:
            kwargs['filters'] = filters

        return extend_schema(**kwargs)(func)

    @staticmethod
    def _apply_yasg(func, summary, description, tags, request_body,
                    responses, manual_parameters, operation_id):
        """Apply drf-yasg documentation"""
        kwargs = {}

        if summary:
            kwargs['operation_summary'] = summary
        if description:
            kwargs['operation_description'] = description
        if tags:
            kwargs['tags'] = tags
        if request_body:
            kwargs['request_body'] = request_body
        if responses:
            kwargs['responses'] = responses
        if manual_parameters:
            kwargs['manual_parameters'] = manual_parameters
        if operation_id:
            kwargs['operation_id'] = operation_id

        return swagger_auto_schema(**kwargs)(func)


# Convenience function for backward compatibility
def keycloak_api_doc(**kwargs):
    """
    Convenience function for KeyCloak API documentation
    Automatically sets common defaults for KeyCloak endpoints
    """
    # Set default tag if not provided
    if 'tags' not in kwargs:
        kwargs['tags'] = ['KeyCloak - Accounts']

    return APIDocumentation.auto_schema(**kwargs)


# Pre-configured decorators for common response patterns
def keycloak_login_doc(**kwargs):
    """Pre-configured decorator for login endpoints"""
    defaults = {
        'tags': ['KeyCloak - Accounts'],
        'responses': {
            200: 'Login successful',
            401: 'Authentication failed',
            400: 'Invalid request data'
        }
    }
    defaults.update(kwargs)
    return APIDocumentation.auto_schema(**defaults)


def keycloak_auth_required_doc(**kwargs):
    """Pre-configured decorator for authenticated endpoints"""
    defaults = {
        'tags': ['KeyCloak - Accounts'],
        'responses': {
            401: 'Authentication required',
            403: 'Permission denied'
        }
    }
    # Merge with existing responses if provided
    if 'responses' in kwargs:
        defaults['responses'].update(kwargs['responses'])
        kwargs.pop('responses')
    defaults.update(kwargs)
    return APIDocumentation.auto_schema(**defaults)


def keycloak_admin_doc(**kwargs):
    """Pre-configured decorator for admin endpoints"""
    defaults = {
        'tags': ['KeyCloak - Admin'],
        'responses': {
            401: 'Authentication required',
            403: 'Admin permission required',
            404: 'Resource not found'
        }
    }
    # Merge with existing responses if provided
    if 'responses' in kwargs:
        defaults['responses'].update(kwargs['responses'])
        kwargs.pop('responses')
    defaults.update(kwargs)
    return APIDocumentation.auto_schema(**defaults)
