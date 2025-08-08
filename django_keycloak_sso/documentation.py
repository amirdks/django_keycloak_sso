
"""
Universal API documentation system compatible with both drf-spectacular and drf-yasg
"""
import logging
from typing import Any, Dict, Optional, Union, List
from copy import deepcopy

logger = logging.getLogger(__name__)

# Try to import both libraries
try:
    from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse
    HAS_SPECTACULAR = True
except ImportError:
    HAS_SPECTACULAR = False
    extend_schema = None

try:
    from drf_yasg.utils import swagger_auto_schema
    from drf_yasg import openapi as yasg_openapi
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
            operation_summary: Optional[str] = None,
            operation_description: Optional[str] = None,
            tags: Optional[List[str]] = None,
            request_body: Optional[Any] = None,
            responses: Optional[Dict[Union[int, str], Any]] = None,
            parameters: Optional[List[Any]] = None,
            examples: Optional[List[Any]] = None,
            deprecated: Optional[bool] = None,
            filters: Optional[bool] = None,
            manual_parameters: Optional[List[Any]] = None,
            operation_id: Optional[str] = None,
            prefer_spectacular: bool = True,
    ):
        def decorator(func):
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

            elif HAS_SPECTACULAR:
                return APIDocumentation._apply_spectacular(
                    func, operation_summary, operation_description, tags,
                    request_body, responses, parameters, examples, deprecated, filters
                )

            elif HAS_YASG:
                return APIDocumentation._apply_yasg(
                    func, operation_summary, operation_description, tags,
                    request_body, responses, manual_parameters, operation_id
                )

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
            kwargs['responses'] = APIDocumentation._normalize_spectacular_responses(responses)
        if parameters:
            kwargs['parameters'] = APIDocumentation._normalize_parameters(parameters)
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
            kwargs['manual_parameters'] = APIDocumentation._normalize_parameters(manual_parameters)
        if operation_id:
            kwargs['operation_id'] = operation_id

        return swagger_auto_schema(**kwargs)(func)

    @staticmethod
    def _normalize_parameters(parameters: Optional[List[Any]]) -> Optional[List[Any]]:
        if not parameters:
            return None

        if HAS_SPECTACULAR:
            normalized = []
            for param in parameters:
                if isinstance(param, dict):
                    normalized.append(OpenApiParameter(
                        name=param.get("name"),
                        type=param.get("type", OpenApiTypes.STR),
                        location=param.get("in", OpenApiParameter.QUERY),
                        required=param.get("required", False),
                        description=param.get("description", "")
                    ))
                else:
                    normalized.append(param)
            return normalized

        elif HAS_YASG:
            normalized = []
            for param in parameters:
                if isinstance(param, dict):
                    normalized.append(yasg_openapi.Parameter(
                        name=param.get("name"),
                        in_=param.get("in", yasg_openapi.IN_QUERY),
                        type=param.get("type", yasg_openapi.TYPE_STRING),
                        required=param.get("required", False),
                        description=param.get("description", "")
                    ))
                else:
                    normalized.append(param)
            return normalized

        return parameters

    @staticmethod
    def _normalize_spectacular_responses(responses: Optional[Dict[Union[int, str], Any]]) -> Optional[Dict[Union[int, str], Any]]:
        if not responses:
            return None

        normalized = {}
        for code, resp in responses.items():
            if isinstance(resp, str):
                normalized[code] = OpenApiResponse(description=resp)
            elif isinstance(resp, dict):
                # dict → فرض می‌کنیم اسکیمای پاسخ هست
                normalized[code] = OpenApiResponse(description="Response", response=resp)
            else:
                # معمولاً serializer یا schema class
                normalized[code] = OpenApiResponse(description="Response", response=resp)

        return normalized


# -----------------------------------------------
# 💡 Shortcut functions for specific use cases
# -----------------------------------------------

def keycloak_api_doc(**kwargs):
    if 'tags' not in kwargs:
        kwargs['tags'] = ['KeyCloak - Accounts']
    return APIDocumentation.auto_schema(**kwargs)


def keycloak_login_doc(**kwargs):
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
    defaults = {
        'tags': ['KeyCloak - Accounts'],
        'responses': {
            401: 'Authentication required',
            403: 'Permission denied'
        }
    }
    if 'responses' in kwargs:
        defaults['responses'].update(kwargs['responses'])
        kwargs.pop('responses')
    defaults.update(kwargs)
    return APIDocumentation.auto_schema(**defaults)


def keycloak_admin_doc(**kwargs):
    defaults = {
        'tags': ['KeyCloak - Admin'],
        'responses': {
            401: 'Authentication required',
            403: 'Admin permission required',
            404: 'Resource not found'
        }
    }
    if 'responses' in kwargs:
        defaults['responses'].update(kwargs['responses'])
        kwargs.pop('responses')
    defaults.update(kwargs)
    return APIDocumentation.auto_schema(**defaults)
